from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

from agents import Agent, Runner, function_tool

from ..config import settings
from ..db import execute_returning, fetch_all, fetch_one
from .llm import evaluate_features

logger = logging.getLogger(__name__)

PENDING_FEATURES_QUERY = """
SELECT f.*
FROM features f
LEFT JOIN evaluations e ON e.feature_id = f.id
WHERE e.id IS NULL
ORDER BY f.extracted_at ASC
LIMIT %s
"""


def _json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=True)


def get_active_goal() -> str:
    row = fetch_one("SELECT value FROM config_store WHERE key = %s", ("active_goal",))
    if not row:
        return "General screenshot quality and user activity overview."
    value = row.get("value") or {}
    if isinstance(value, dict):
        return (
            value.get("goal")
            or value.get("text")
            or "General screenshot quality and user activity overview."
        )
    return str(value)


def fetch_pending_features(limit: int = 10) -> list[dict]:
    return fetch_all(PENDING_FEATURES_QUERY, (limit,))


def fetch_feature(feature_id: str) -> dict | None:
    return fetch_one("SELECT * FROM features WHERE id = %s", (feature_id,))


def process_feature(feature: dict) -> None:
    goal = get_active_goal()
    features_payload = feature.get("features") or {}
    evaluation = evaluate_features(goal, features_payload)

    row = execute_returning(
        """
        INSERT INTO evaluations (feature_id, evaluation, goal, evaluated_at, model)
        VALUES (%s, %s::jsonb, %s, %s, %s)
        RETURNING id
        """,
        (
            feature["id"],
            _json(evaluation),
            goal,
            datetime.now(timezone.utc),
            settings.openai_model,
        ),
    )
    logger.info("Evaluated feature %s -> %s", feature["id"], row["id"] if row else "?")


@function_tool
def evaluate_feature(feature_id: str) -> str:
    feature = fetch_feature(feature_id)
    if not feature:
        return "feature_not_found"
    process_feature(feature)
    return "ok"


def _build_agent() -> Agent:
    kwargs = {
        "name": "EvaluationManager",
        "instructions": (
            "You manage evaluation jobs. Always call the evaluate_feature tool with the feature_id from the input."
        ),
        "tools": [evaluate_feature],
    }
    if settings.openai_model:
        kwargs["model"] = settings.openai_model
    return Agent(**kwargs)


def run_agent(feature_id: str) -> None:
    if not settings.openai_api_key:
        evaluate_feature(feature_id)
        return
    agent = _build_agent()
    Runner.run_sync(agent, json.dumps({"feature_id": feature_id}, ensure_ascii=True))


def run() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    logger.info("Starting evaluation manager agent")
    while True:
        pending = fetch_pending_features()
        if not pending:
            time.sleep(settings.agent_interval_seconds)
            continue
        for feature in pending:
            try:
                run_agent(str(feature["id"]))
            except Exception:
                logger.exception("Failed to evaluate feature %s", feature.get("id"))
        time.sleep(1)


if __name__ == "__main__":
    run()
