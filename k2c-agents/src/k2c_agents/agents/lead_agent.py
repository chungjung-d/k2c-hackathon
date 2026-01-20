from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone

from agents import Agent, Runner, function_tool

from ..config import settings
from ..db import execute, fetch_one

logger = logging.getLogger(__name__)


def upsert_config(key: str, value: dict) -> None:
    execute(
        """
        INSERT INTO config_store (key, value, updated_at)
        VALUES (%s, %s::jsonb, %s)
        ON CONFLICT (key)
        DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
        """,
        (key, json.dumps(value, ensure_ascii=True), datetime.now(timezone.utc)),
    )


def get_config(key: str) -> dict | None:
    row = fetch_one("SELECT value FROM config_store WHERE key = %s", (key,))
    return row.get("value") if row else None


@function_tool
def set_goal(goal: str) -> str:
    upsert_config("active_goal", {"goal": goal})
    return "updated_active_goal"


@function_tool(strict_mode=False)
def set_config(key: str, value: dict) -> str:
    upsert_config(key, value)
    return "updated_config"


@function_tool
def get_config_tool(key: str) -> dict | None:
    return get_config(key)


def _build_agent() -> Agent:
    kwargs = {
        "name": "LeadAgent",
        "instructions": (
            "You are the lead agent. The input is JSON with a command field. "
            "Always call exactly one tool based on command: set-goal, set-config, get-config."
        ),
        "tools": [set_goal, set_config, get_config_tool],
    }
    if settings.openai_model:
        kwargs["model"] = settings.openai_model
    return Agent(**kwargs)


def run_agent(payload: dict) -> object:
    if not settings.openai_api_key:
        command = payload.get("command")
        if command == "set-goal":
            return set_goal(payload["goal"])
        if command == "set-config":
            return set_config(payload["key"], payload["value"])
        if command == "get-config":
            return get_config_tool(payload["key"])
        raise ValueError("Unknown command")
    agent = _build_agent()
    result = Runner.run_sync(agent, json.dumps(payload, ensure_ascii=True))
    return result.final_output


def run() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    parser = argparse.ArgumentParser(description="Lead agent: manage goals and config")
    sub = parser.add_subparsers(dest="command", required=True)

    set_goal = sub.add_parser("set-goal", help="Set the active evaluation goal")
    set_goal.add_argument("goal", help="Goal text")

    set_config = sub.add_parser(
        "set-config", help="Set an arbitrary config key (JSON value)"
    )
    set_config.add_argument("key", help="Config key")
    set_config.add_argument("json", help="JSON string value")

    get_config_cmd = sub.add_parser("get-config", help="Get a config key")
    get_config_cmd.add_argument("key", help="Config key")

    args = parser.parse_args()

    if args.command == "set-goal":
        run_agent({"command": "set-goal", "goal": args.goal})
        logger.info("Updated active_goal")
        return

    if args.command == "set-config":
        value = json.loads(args.json)
        run_agent({"command": "set-config", "key": args.key, "value": value})
        logger.info("Updated config %s", args.key)
        return

    if args.command == "get-config":
        value = run_agent({"command": "get-config", "key": args.key})
        print(json.dumps(value, indent=2))
        return


if __name__ == "__main__":
    run()
