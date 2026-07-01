"""Approval state machine models shared by service and persistence layers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ApprovalState(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING_TIMEOUT = "pending_timeout"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


class ApprovalRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    correlation_id: str
    tool_name: str
    params: dict[str, Any]
    requested_by: str
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    timeout_sec: float
    safe_default: str
    state: ApprovalState = ApprovalState.REQUESTED
    decided_by: str | None = None
    decided_at: datetime | None = None
    decision_reason: str | None = None
    meaning_of_signature: str | None = None
