from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class IndexRequest(BaseModel):
    event: dict[str, Any]
    features: dict[str, Any]
    feature_id: str | None = None
    received_at: str | None = None


class IndexResponse(BaseModel):
    job_id: str
