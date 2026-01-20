from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .agents.lead_agent import handle_lead_message
from .config import settings
from .schemas import LeadMessageIn, LeadMessageOut

logger = logging.getLogger(__name__)

app = FastAPI(title="k2c-lead-agent")

_MAX_HISTORY = 20
_SESSIONS: dict[str, list[dict[str, str]]] = {}


@app.on_event("startup")
def _startup() -> None:
    logging.basicConfig(
        level=getattr(logging, (settings.log_level or "INFO").upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Lead agent server started")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/lead/message", response_model=LeadMessageOut)
def lead_message(payload: LeadMessageIn) -> LeadMessageOut:
    session_id = payload.session_id or str(uuid.uuid4())
    history = _SESSIONS.get(session_id, [])
    result = handle_lead_message(
        payload.message, history, max_rounds=payload.max_rounds
    )
    assistant_message = result.get("message") or ""
    history.append({"role": "user", "content": payload.message})
    history.append({"role": "assistant", "content": assistant_message})
    _SESSIONS[session_id] = history[-_MAX_HISTORY:]

    return LeadMessageOut(
        session_id=session_id,
        message=assistant_message,
        updated=bool(result.get("updated")),
        goals=result.get("goals"),
    )


@app.exception_handler(Exception)
async def _unhandled_exception(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


def run() -> None:
    import uvicorn

    uvicorn.run(
        "k2c_agents.lead_server:app",
        host="0.0.0.0",
        port=settings.lead_server_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
