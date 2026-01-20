from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EventResponse(BaseModel):
    event_id: str
    object_key: str


class ConfigValue(BaseModel):
    value: dict[str, Any]


class ConfigResponse(BaseModel):
    key: str
    value: dict[str, Any]
    updated_at: datetime


class LeadMessageIn(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    max_rounds: int | None = None


class LeadMessageOut(BaseModel):
    session_id: str
    message: str
    updated: bool = False
    goals: dict[str, Any] | None = None
