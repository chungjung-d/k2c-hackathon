from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..config import settings
from ..db import execute, execute_returning, fetch_all, fetch_one
from ..storage import stat_object
from .llm import analyze_screenshot, summarize_event

logger = logging.getLogger(__name__)

PENDING_EVENTS_QUERY = """
SELECT d.*
FROM data_events d
LEFT JOIN features f ON f.event_id = d.id
WHERE f.id IS NULL
ORDER BY d.received_at ASC
LIMIT %s
"""


def _json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=True)


def fetch_pending_events(limit: int = 10) -> list[dict]:
    return fetch_all(PENDING_EVENTS_QUERY, (limit,))


def fetch_event(event_id: str) -> dict | None:
    return fetch_one("SELECT * FROM data_events WHERE id = %s", (event_id,))


def _value_to_goal(value: object, default: str) -> str:
    if value is None:
        return default
    if isinstance(value, dict):
        return value.get("goal") or value.get("text") or default
    return str(value)


def get_preprocess_goal() -> str:
    row = fetch_one(
        "SELECT value FROM config_store WHERE key = %s", ("preprocess_goal",)
    )
    if row:
        return _value_to_goal(
            row.get("value"),
            "Extract compact, structured features from screenshots for downstream use.",
        )
    return "Extract compact, structured features from screenshots for downstream use."


def _indexer_url(path: str) -> str:
    base = (settings.indexer_api_base_url or "").rstrip("/")
    if not base:
        return ""
    return f"{base}{path}"


def _send_to_indexer(payload: dict) -> None:
    url = _indexer_url("/index")
    if not url:
        return
    body = _json(payload).encode("utf-8")
    request = Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    try:
        with urlopen(request, timeout=10) as response:
            response.read()
    except (HTTPError, URLError) as exc:
        logger.warning("Failed to send payload to indexer: %s", exc)


def process_event(event: dict) -> None:
    metadata = event.get("metadata") or {}
    goal = get_preprocess_goal()
    extra = {
        "object": stat_object(event["object_key"]),
        "content_type": event.get("content_type"),
        "size_bytes": event.get("size_bytes"),
        "sha256": event.get("sha256"),
    }
    content_type = (
        event.get("content_type")
        or (extra.get("object") or {}).get("content_type")
        or "application/octet-stream"
    )
    if content_type.startswith("image/"):
        analysis = analyze_screenshot(
            event["object_key"], content_type, metadata, extra
        )
    else:
        analysis = summarize_event(metadata, extra, goal=goal)

    summary_text = analysis.get("content_summary") or analysis.get("summary")
    features_payload = {
        "summary": summary_text,
        "content_summary": analysis.get("content_summary", summary_text),
        "user_activity": analysis.get("user_activity", ""),
        "ocr_text": analysis.get("ocr_text", ""),
        "ocr_source": analysis.get("ocr_source", "unknown"),
        "tags": analysis.get("tags", []),
        "risk_level": analysis.get("risk_level", "unknown"),
        "metadata": metadata,
        "object": extra.get("object"),
        "sha256": extra.get("sha256"),
        "source": analysis.get("source", "unknown"),
    }

    row = execute_returning(
        """
        INSERT INTO features (event_id, features, extracted_at, model)
        VALUES (%s, %s::jsonb, %s, %s)
        RETURNING id
        """,
        (
            event["id"],
            _json(features_payload),
            datetime.now(timezone.utc),
            settings.openai_model,
        ),
    )
    execute(
        "UPDATE data_events SET processed_at = %s WHERE id = %s",
        (datetime.now(timezone.utc), event["id"]),
    )
    index_payload = {
        "event": {
            "id": str(event["id"]),
            "user_id": event.get("user_id"),
            "captured_at": event.get("captured_at").isoformat()
            if event.get("captured_at")
            else None,
            "object_key": event.get("object_key"),
            "content_type": event.get("content_type"),
            "size_bytes": event.get("size_bytes"),
            "sha256": event.get("sha256"),
        },
        "feature_id": str(row["id"]) if row else None,
        "features": features_payload,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    _send_to_indexer(index_payload)
    logger.info(
        "Extracted features for event %s -> %s", event["id"], row["id"] if row else "?"
    )


def extract_features(event_id: str) -> str:
    event = fetch_event(event_id)
    if not event:
        return "event_not_found"
    process_event(event)
    return "ok"


def run_agent(event_id: str) -> None:
    # Avoid nested agent runs: extract_features already calls the LLM via Runner.
    extract_features(event_id)


def run() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    logger.info("Starting preprocess manager agent")
    while True:
        pending = fetch_pending_events()
        if not pending:
            time.sleep(settings.agent_interval_seconds)
            continue
        for event in pending:
            try:
                run_agent(str(event["id"]))
            except Exception:
                logger.exception("Failed to process event %s", event.get("id"))
        time.sleep(1)


if __name__ == "__main__":
    run()
