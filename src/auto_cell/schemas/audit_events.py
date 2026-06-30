"""Unified audit / event-store Pydantic models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class EventType(str, Enum):
    TELEMETRY = "telemetry"
    EVENT = "event"
    COMMAND = "command"
    ACK = "ack"
    APPROVAL = "approval"
    TOOL_EXEC = "tool_execution"
    AUDIT = "audit"
    SYSTEM = "system"


class EventHeader(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: Literal["1.0"] = "1.0"
    run_id: str
    correlation_id: str | None = None
    parent_event_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    actor: str
    event_type: EventType


class Event(BaseModel):
    """One JSONL line in the event store."""

    model_config = {"frozen": True, "extra": "forbid"}

    header: EventHeader
    payload: dict[str, Any]


class TelemetryPayload(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    channel: str
    value: float | int | str | None
    unit: str | None = None
    quality: Literal["good", "suspect", "bad"] = "good"


class CommandPayload(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    tool_name: str
    args: dict[str, Any]
    request_id: str


class ApprovalPayload(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    request_id: str
    tool_name: str
    params: dict[str, Any]
    state: Literal[
        "requested",
        "approved",
        "rejected",
        "pending_timeout",
        "executed",
        "cancelled",
    ]
    requested_by: str
    decided_by: str | None = None
    reason: str | None = None
    timeout_sec: float
    safe_default: Literal["cancel", "reject", "hold"] | None = None
