from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EventResponse(BaseModel):
    event_id: str
    object_key: str


class ConfigValue(BaseModel):
    value: dict[str, Any]


class ConfigResponse(BaseModel):
    key: str
    value: dict[str, Any]
    updated_at: datetime
