from __future__ import annotations

import argparse
import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from agents import Agent, Runner, function_tool
from pydantic import BaseModel, Field

from ..config import settings

logger = logging.getLogger(__name__)

DEFAULT_PREPROCESS_GOAL = (
    "Extract compact, structured features from screenshots for downstream use."
)
MAX_DISCUSSION_ROUNDS = 10


class ManagerGoalProposal(BaseModel):
    goal: str = Field(..., min_length=1)
    rationale: str = ""
    focus_areas: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    needs_more_discussion: bool = False


class LeadConversationDecision(BaseModel):
    message: str
    update_goal: bool = False
    goal: str | None = None
    max_rounds: int | None = None


def _resolve_log_level() -> int:
    level_name = (settings.log_level or "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


def _config_base_url() -> str:
    base = (settings.config_api_base_url or "").rstrip("/")
    if not base:
        raise ValueError("CONFIG_API_BASE_URL is empty")
    return base


def _request_json(
    method: str, url: str, payload: dict | None = None, allow_not_found: bool = False
) -> dict | None:
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    req = Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=10) as resp:
            body = resp.read()
            if not body:
                return None
            return json.loads(body.decode("utf-8"))
    except HTTPError as exc:
        if allow_not_found and exc.code == 404:
            return None
        body = ""
        if exc.fp:
            body = exc.fp.read().decode("utf-8")
        detail = body or exc.reason
        raise RuntimeError(f"Config API request failed ({exc.code}): {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Config API unavailable: {exc.reason}") from exc


def _config_url(key: str) -> str:
    return f"{_config_base_url()}/config/{key}"


def _lead_base_url() -> str:
    base = (settings.lead_api_base_url or "").rstrip("/")
    if not base:
        raise ValueError("LEAD_API_BASE_URL is empty")
    return base


def _lead_url(path: str) -> str:
    return f"{_lead_base_url()}{path}"


def upsert_config(key: str, value: dict) -> None:
    _request_json("PUT", _config_url(key), {"value": value})


def get_config(key: str) -> dict | None:
    response = _request_json("GET", _config_url(key), allow_not_found=True)
    if not response:
        return None
    return response.get("value")


def send_lead_message(
    message: str, session_id: str | None = None, max_rounds: int | None = None
) -> dict | None:
    payload: dict[str, Any] = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    if max_rounds is not None:
        payload["max_rounds"] = max_rounds
    return _request_json("POST", _lead_url("/lead/message"), payload=payload)


@function_tool
def set_goal(goal: str) -> str:
    upsert_config("lead_goal", {"goal": goal})
    upsert_config("active_goal", {"goal": goal})
    return "updated_lead_goal"


@function_tool(strict_mode=False)
def set_config(key: str, value: dict) -> str:
    upsert_config(key, value)
    return "updated_config"


@function_tool
def get_config_tool(key: str) -> dict | None:
    return get_config(key)


def _proposal_to_dict(proposal: ManagerGoalProposal) -> dict[str, Any]:
    return {
        "goal": proposal.goal,
        "rationale": proposal.rationale,
        "focus_areas": proposal.focus_areas,
        "questions": proposal.questions,
        "needs_more_discussion": proposal.needs_more_discussion,
    }


def _build_manager_goal_agent(name: str, role: str) -> Agent:
    instructions = (
        f"You are the {name} agent responsible for {role}. "
        "Given the lead goal and any prior context, propose a concise, actionable "
        "goal for your pipeline. Keep it short (1-2 sentences). "
        "If you need clarification or alignment with the other manager, set "
        "needs_more_discussion to true and include questions."
    )
    kwargs = {
        "name": f"{name}GoalAgent",
        "instructions": instructions,
        "output_type": ManagerGoalProposal,
    }
    if settings.openai_model:
        kwargs["model"] = settings.openai_model
    return Agent(**kwargs)


def _run_goal_agent(
    agent: Agent,
    payload: dict[str, Any],
    default_goal: str,
    default_reason: str,
) -> ManagerGoalProposal:
    if not settings.openai_api_key:
        return ManagerGoalProposal(goal=default_goal, rationale=default_reason)
    try:
        result = Runner.run_sync(agent, json.dumps(payload, ensure_ascii=True))
        output = result.final_output
        if isinstance(output, ManagerGoalProposal):
            return output
        return ManagerGoalProposal.model_validate(output)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Goal coordination failed: %s", exc)
        return ManagerGoalProposal(goal=default_goal, rationale=default_reason)


def set_goal_bundle(
    lead_goal: str,
    preprocess_goal: str,
    evaluation_goal: str,
    coordination: dict[str, Any] | None = None,
) -> None:
    upsert_config("lead_goal", {"goal": lead_goal})
    upsert_config("active_goal", {"goal": lead_goal})
    upsert_config("preprocess_goal", {"goal": preprocess_goal})
    upsert_config("evaluation_goal", {"goal": evaluation_goal})
    if coordination is not None:
        upsert_config("goal_coordination", coordination)


def _prepare_coordination_payload(
    lead_goal: str,
    round_index: int,
    previous_goal: str | None,
    counterpart_goal: str | None,
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "lead_goal": lead_goal,
        "round": round_index,
        "previous_goal": previous_goal,
        "counterpart_goal": counterpart_goal,
        "history": history,
    }


def coordinate_goals(
    lead_goal: str, max_rounds: int = MAX_DISCUSSION_ROUNDS
) -> dict[str, Any]:
    cleaned_goal = lead_goal.strip()
    if not cleaned_goal:
        raise ValueError("lead goal must be non-empty")

    rounds = max(1, min(MAX_DISCUSSION_ROUNDS, max_rounds))
    if not settings.openai_api_key:
        logger.debug("Goal coordination fallback: OPENAI_API_KEY not set.")
        preprocess_goal = DEFAULT_PREPROCESS_GOAL
        evaluation_goal = cleaned_goal
        set_goal_bundle(
            cleaned_goal,
            preprocess_goal,
            evaluation_goal,
            coordination={"mode": "fallback", "rounds": 0},
        )
        return {
            "lead_goal": cleaned_goal,
            "preprocess_goal": preprocess_goal,
            "evaluation_goal": evaluation_goal,
            "rounds": 0,
        }

    preprocess_agent = _build_manager_goal_agent(
        "PreprocessManager", "preprocessing and feature extraction"
    )
    evaluation_agent = _build_manager_goal_agent(
        "EvaluationManager", "evaluation and scoring"
    )

    history: list[dict[str, Any]] = []
    preprocess_goal: str | None = None
    evaluation_goal: str | None = None

    for round_index in range(1, rounds + 1):
        logger.debug(
            "Discussion round %s start: lead_goal=%s", round_index, cleaned_goal
        )
        preprocess_payload = _prepare_coordination_payload(
            cleaned_goal, round_index, preprocess_goal, evaluation_goal, history[-2:]
        )
        preprocess_proposal = _run_goal_agent(
            preprocess_agent,
            preprocess_payload,
            DEFAULT_PREPROCESS_GOAL,
            "Fallback preprocess goal.",
        )
        logger.debug(
            "Round %s preprocess proposal: %s",
            round_index,
            _proposal_to_dict(preprocess_proposal),
        )

        evaluation_payload = _prepare_coordination_payload(
            cleaned_goal,
            round_index,
            evaluation_goal,
            preprocess_proposal.goal,
            history[-2:],
        )
        evaluation_proposal = _run_goal_agent(
            evaluation_agent,
            evaluation_payload,
            cleaned_goal,
            "Fallback evaluation goal.",
        )
        logger.debug(
            "Round %s evaluation proposal: %s",
            round_index,
            _proposal_to_dict(evaluation_proposal),
        )

        new_preprocess_goal = (
            preprocess_proposal.goal.strip() or DEFAULT_PREPROCESS_GOAL
        )
        new_evaluation_goal = evaluation_proposal.goal.strip() or cleaned_goal

        history.append(
            {
                "round": round_index,
                "preprocess": _proposal_to_dict(preprocess_proposal),
                "evaluation": _proposal_to_dict(evaluation_proposal),
            }
        )

        stabilized = (
            preprocess_goal == new_preprocess_goal
            and evaluation_goal == new_evaluation_goal
        )
        preprocess_goal = new_preprocess_goal
        evaluation_goal = new_evaluation_goal

        if (
            not preprocess_proposal.needs_more_discussion
            and not evaluation_proposal.needs_more_discussion
            and stabilized
        ):
            logger.debug("Discussion stabilized at round %s.", round_index)
            break

    final_preprocess_goal = preprocess_goal or DEFAULT_PREPROCESS_GOAL
    final_evaluation_goal = evaluation_goal or cleaned_goal

    set_goal_bundle(
        cleaned_goal,
        final_preprocess_goal,
        final_evaluation_goal,
        coordination={
            "rounds": len(history),
            "history": history,
        },
    )
    return {
        "lead_goal": cleaned_goal,
        "preprocess_goal": final_preprocess_goal,
        "evaluation_goal": final_evaluation_goal,
        "rounds": len(history),
    }


def _build_conversation_agent() -> Agent:
    instructions = (
        "You are the lead agent chatting with a user. "
        "Decide whether the user's latest message contains a clear goal. "
        "If it does, set update_goal true and provide the goal text. "
        "If it does not, ask one concise clarification question and set update_goal false. "
        "Keep responses short and actionable."
    )
    kwargs = {
        "name": "LeadConversationAgent",
        "instructions": instructions,
        "output_type": LeadConversationDecision,
    }
    if settings.openai_model:
        kwargs["model"] = settings.openai_model
    return Agent(**kwargs)


def decide_lead_action(
    message: str, history: list[dict[str, str]]
) -> LeadConversationDecision:
    cleaned = message.strip()
    if not cleaned:
        return LeadConversationDecision(
            message="Tell me the goal you want to achieve.", update_goal=False
        )
    if not settings.openai_api_key:
        return LeadConversationDecision(
            message="Got it. Updating goals.", update_goal=True, goal=cleaned
        )
    payload = json.dumps({"message": cleaned, "history": history}, ensure_ascii=True)
    agent = _build_conversation_agent()
    try:
        result = Runner.run_sync(agent, payload)
        output = result.final_output
        if isinstance(output, LeadConversationDecision):
            return output
        return LeadConversationDecision.model_validate(output)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Lead conversation failed: %s", exc)
        return LeadConversationDecision(
            message="Please restate the goal you want to set.", update_goal=False
        )


def handle_lead_message(
    message: str,
    history: list[dict[str, str]],
    max_rounds: int | None = None,
) -> dict[str, Any]:
    decision = decide_lead_action(message, history)
    response_text = decision.message or "Acknowledged."
    if decision.update_goal:
        goal_text = (decision.goal or message).strip()
        if not goal_text:
            return {"message": "Please provide a goal to proceed.", "updated": False}
        rounds = max_rounds or decision.max_rounds or MAX_DISCUSSION_ROUNDS
        goals = coordinate_goals(goal_text, max_rounds=rounds)
        return {"message": response_text, "updated": True, "goals": goals}
    return {"message": response_text, "updated": False}


@function_tool
def coordinate_goals_tool(goal: str, max_rounds: int = MAX_DISCUSSION_ROUNDS) -> dict:
    return coordinate_goals(goal, max_rounds=max_rounds)


def _build_agent() -> Agent:
    kwargs = {
        "name": "LeadAgent",
        "instructions": (
            "You are the lead agent. The input is JSON with a command field. "
            "Always call exactly one tool based on command: set-goal, "
            "coordinate-goals, set-config, get-config."
        ),
        "tools": [set_goal, coordinate_goals_tool, set_config, get_config_tool],
    }
    if settings.openai_model:
        kwargs["model"] = settings.openai_model
    return Agent(**kwargs)


def run_agent(payload: dict) -> object:
    if not settings.openai_api_key:
        command = payload.get("command")
        if command == "set-goal":
            return set_goal(payload["goal"])
        if command == "coordinate-goals":
            return coordinate_goals(
                payload["goal"], payload.get("max_rounds", MAX_DISCUSSION_ROUNDS)
            )
        if command == "set-config":
            return set_config(payload["key"], payload["value"])
        if command == "get-config":
            return get_config_tool(payload["key"])
        raise ValueError("Unknown command")
    agent = _build_agent()
    result = Runner.run_sync(agent, json.dumps(payload, ensure_ascii=True))
    return result.final_output


def _goal_status() -> dict[str, Any]:
    return {
        "lead_goal": get_config("lead_goal"),
        "preprocess_goal": get_config("preprocess_goal"),
        "evaluation_goal": get_config("evaluation_goal"),
        "goal_coordination": get_config("goal_coordination"),
    }


def _print_status() -> None:
    print(json.dumps(_goal_status(), indent=2, ensure_ascii=True))


def _run_session(max_rounds: int) -> None:
    print("Lead agent session started. Type /help for commands.")
    while True:
        try:
            line = input("lead> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("")
            break
        if not line:
            continue
        if line in {"/exit", "/quit"}:
            break
        if line == "/help":
            print("/goal <text>  set a new lead goal and coordinate manager goals")
            print("/status       show current stored goals")
            print("/exit         quit the session")
            continue
        if line == "/status":
            _print_status()
            continue
        if line.startswith("/goal "):
            goal_text = line[len("/goal ") :].strip()
        else:
            goal_text = line
        if not goal_text:
            continue
        result = coordinate_goals(goal_text, max_rounds=max_rounds)
        print(json.dumps(result, indent=2, ensure_ascii=True))


def run() -> None:
    logging.basicConfig(
        level=_resolve_log_level(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Lead agent: coordinate goals and config"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    set_goal_cmd = sub.add_parser(
        "set-goal", help="Set the lead goal and coordinate manager goals"
    )
    set_goal_cmd.add_argument("goal", help="Goal text")
    set_goal_cmd.add_argument(
        "--max-rounds",
        type=int,
        default=MAX_DISCUSSION_ROUNDS,
        help="Max discussion rounds with manager agents (default: 10)",
    )
    set_goal_cmd.add_argument(
        "--direct",
        action="store_true",
        help="Run coordination locally instead of via lead server",
    )
    set_goal_cmd.add_argument(
        "--no-coordinate",
        action="store_true",
        help="Only update the lead goal (skip coordination)",
    )

    coordinate_cmd = sub.add_parser(
        "coordinate", help="Coordinate manager goals for a lead goal"
    )
    coordinate_cmd.add_argument("goal", help="Goal text")
    coordinate_cmd.add_argument(
        "--max-rounds",
        type=int,
        default=MAX_DISCUSSION_ROUNDS,
        help="Max discussion rounds with manager agents (default: 10)",
    )

    set_config_cmd = sub.add_parser(
        "set-config", help="Set an arbitrary config key (JSON value)"
    )
    set_config_cmd.add_argument("key", help="Config key")
    set_config_cmd.add_argument("json", help="JSON string value")

    get_config_cmd = sub.add_parser("get-config", help="Get a config key")
    get_config_cmd.add_argument("key", help="Config key")

    session_cmd = sub.add_parser(
        "session", help="Run an interactive lead agent session"
    )
    session_cmd.add_argument(
        "--max-rounds",
        type=int,
        default=MAX_DISCUSSION_ROUNDS,
        help="Max discussion rounds with manager agents (default: 10)",
    )

    args = parser.parse_args()

    if args.command == "set-goal":
        if args.no_coordinate:
            run_agent({"command": "set-goal", "goal": args.goal})
            logger.info("Updated lead_goal")
            print(json.dumps(_goal_status(), indent=2, ensure_ascii=True))
            return
        if not args.direct and settings.lead_api_base_url:
            try:
                response = send_lead_message(args.goal, max_rounds=args.max_rounds)
                print(json.dumps(response, indent=2, ensure_ascii=True))
                return
            except RuntimeError as exc:
                logger.warning("Lead server unavailable; falling back: %s", exc)
        result = run_agent(
            {
                "command": "coordinate-goals",
                "goal": args.goal,
                "max_rounds": args.max_rounds,
            }
        )
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return

    if args.command == "coordinate":
        result = run_agent(
            {
                "command": "coordinate-goals",
                "goal": args.goal,
                "max_rounds": args.max_rounds,
            }
        )
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return

    if args.command == "set-config":
        value = json.loads(args.json)
        run_agent({"command": "set-config", "key": args.key, "value": value})
        logger.info("Updated config %s", args.key)
        return

    if args.command == "get-config":
        value = run_agent({"command": "get-config", "key": args.key})
        print(json.dumps(value, indent=2, ensure_ascii=True))
        return

    if args.command == "session":
        _run_session(args.max_rounds)
        return


if __name__ == "__main__":
    run()
