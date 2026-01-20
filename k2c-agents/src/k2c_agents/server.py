from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .config import settings
from .db import execute, execute_returning, fetch_one
from .schemas import ConfigResponse, ConfigValue, EventResponse
from .storage import ensure_bucket, put_bytes

logger = logging.getLogger(__name__)

app = FastAPI(title="k2c-collector-proxy")

DEFAULT_PREPROCESS_GOAL = (
    "Extract compact, structured features from screenshots for downstream use."
)


@app.on_event("startup")
def _startup() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    ensure_bucket()
    _ensure_default_goals()
    logger.info("Collector proxy started")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=True)


def _insert_config_if_missing(key: str, value: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc)
    execute(
        """
        INSERT INTO config_store (key, value, updated_at)
        VALUES (%s, %s::jsonb, %s)
        ON CONFLICT (key) DO NOTHING
        """,
        (key, _json(value), now),
    )


def _ensure_default_goals() -> None:
    preprocess_row = fetch_one(
        "SELECT value FROM config_store WHERE key = %s", ("preprocess_goal",)
    )
    if not preprocess_row:
        _insert_config_if_missing("preprocess_goal", {"goal": DEFAULT_PREPROCESS_GOAL})


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _store_event(
    user_id: str,
    image_bytes: bytes,
    content_type: str,
    captured_at: datetime | None,
    metadata: dict[str, Any] | None,
) -> EventResponse:
    now = datetime.now(timezone.utc)
    captured_at = captured_at or now
    object_key = f"events/{user_id}/{uuid.uuid4()}"
    sha256 = _hash_bytes(image_bytes)
    size_bytes = len(image_bytes)

    put_bytes(object_key, image_bytes, content_type=content_type)

    row = execute_returning(
        """
        INSERT INTO data_events (
            user_id, captured_at, received_at, content_type, size_bytes, sha256, object_key, metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        RETURNING id
        """,
        (
            user_id,
            captured_at,
            now,
            content_type,
            size_bytes,
            sha256,
            object_key,
            _json(metadata or {}),
        ),
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to insert event")
    return EventResponse(event_id=str(row["id"]), object_key=object_key)


@app.post("/event", response_model=EventResponse)
async def post_event(request: Request) -> EventResponse:
    form = await request.form()
    upload = form.get("image")
    if upload is None:
        raise HTTPException(status_code=400, detail="Missing image file")

    user_id = str(form.get("user_id") or "anonymous")
    captured_at = _parse_datetime(form.get("captured_at"))
    metadata_raw = form.get("metadata")
    metadata = {}
    if metadata_raw:
        try:
            metadata = json.loads(metadata_raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=400, detail="Invalid metadata JSON"
            ) from exc

    image_bytes = await upload.read()
    return _store_event(
        user_id=user_id,
        image_bytes=image_bytes,
        content_type=upload.content_type or "application/octet-stream",
        captured_at=captured_at,
        metadata=metadata,
    )


@app.get("/config/{key}", response_model=ConfigResponse)
def get_config(key: str) -> ConfigResponse:
    row = fetch_one(
        "SELECT key, value, updated_at FROM config_store WHERE key = %s", (key,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Config not found")
    return ConfigResponse(
        key=row["key"], value=row["value"], updated_at=row["updated_at"]
    )


@app.put("/config/{key}", response_model=ConfigResponse)
def put_config(key: str, payload: ConfigValue) -> ConfigResponse:
    now = datetime.now(timezone.utc)
    execute(
        """
        INSERT INTO config_store (key, value, updated_at)
        VALUES (%s, %s::jsonb, %s)
        ON CONFLICT (key)
        DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
        """,
        (key, _json(payload.value), now),
    )
    return ConfigResponse(key=key, value=payload.value, updated_at=now)


@app.exception_handler(Exception)
async def _unhandled_exception(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


def run() -> None:
    import uvicorn

    uvicorn.run("k2c_agents.server:app", host="0.0.0.0", port=8001, reload=False)


if __name__ == "__main__":
    run()
