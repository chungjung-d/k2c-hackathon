from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .config import settings
from .db import execute_returning
from .schemas import IndexRequest, IndexResponse

logger = logging.getLogger(__name__)

app = FastAPI(title="k2c-indexer-server")


@app.on_event("startup")
def _startup() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    logger.info("Indexer server started")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=True)


@app.post("/index", response_model=IndexResponse)
async def enqueue_index(request: Request) -> IndexResponse:
    raw_body = await request.body()
    if not raw_body:
        raise HTTPException(status_code=400, detail="Missing request body")
    try:
        raw_request = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    try:
        payload = IndexRequest.model_validate(raw_request)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid index payload") from exc

    now = datetime.now(timezone.utc)
    row = execute_returning(
        """
        INSERT INTO index_jobs (raw_request, payload, status, enqueued_at)
        VALUES (%s::jsonb, %s::jsonb, %s, %s)
        RETURNING id
        """,
        (_json(raw_request), _json(payload.model_dump()), "pending", now),
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to enqueue index job")
    return IndexResponse(job_id=str(row["id"]))


@app.exception_handler(Exception)
async def _unhandled_exception(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


def run() -> None:
    import uvicorn

    uvicorn.run(
        "k2c_indexer.server:app",
        host="0.0.0.0",
        port=settings.indexer_server_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
