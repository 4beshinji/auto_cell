"""Approval state machine, queue, and timeout handling."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from auto_cell.audit.audit_log import AuditLog
from auto_cell.audit.event_store import EventWriter
from auto_cell.hmi.approval_matrix import ApprovalMatrix
from auto_cell.schemas.audit_events import EventType


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


class ApprovalService:
    def __init__(
        self,
        event_writer: EventWriter,
        audit_log: AuditLog,
        matrix: ApprovalMatrix | None = None,
    ):
        self._requests: dict[str, ApprovalRequest] = {}
        self._timeouts: dict[str, asyncio.Task[Any]] = {}
        self.event_writer = event_writer
        self.audit_log = audit_log
        self.matrix = matrix

    async def request(
        self,
        run_id: str,
        tool_name: str,
        params: dict[str, Any],
        requested_by: str,
        timeout_sec: float,
        safe_default: str,
        correlation_id: str,
        reason: str,
    ) -> ApprovalRequest:
        req = ApprovalRequest(
            run_id=run_id,
            correlation_id=correlation_id,
            tool_name=tool_name,
            params=params,
            requested_by=requested_by,
            timeout_sec=timeout_sec,
            safe_default=safe_default,
        )
        self._requests[req.request_id] = req
        self._log(req, "approval_requested", reason)
        self._timeouts[req.request_id] = asyncio.create_task(
            self._timeout_handler(req.request_id, timeout_sec)
        )
        return req

    async def _timeout_handler(self, request_id: str, delay: float) -> None:
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        req = self._requests.get(request_id)
        if not req or req.state != ApprovalState.REQUESTED:
            return
        if req.safe_default in ("cancel", "reject"):
            req.state = ApprovalState.PENDING_TIMEOUT
            self._finalize(req, ApprovalState.CANCELLED, "system", f"timeout safe_default={req.safe_default}")
        elif req.safe_default == "hold":
            req.state = ApprovalState.PENDING_TIMEOUT
            self._log(req, "approval_pending_timeout", "awaiting human decision beyond timeout")

    def approve(self, request_id: str, actor: str, reason: str) -> ApprovalRequest:
        req = self._get_open(request_id)
        self._finalize(req, ApprovalState.APPROVED, actor, reason)
        return req

    def reject(self, request_id: str, actor: str, reason: str) -> ApprovalRequest:
        req = self._get_open(request_id)
        self._finalize(req, ApprovalState.REJECTED, actor, reason)
        return req

    def execute(self, request_id: str, actor: str = "system") -> ApprovalRequest:
        req = self._requests.get(request_id)
        if not req or req.state != ApprovalState.APPROVED:
            raise ValueError("request must be approved before execute")
        req.state = ApprovalState.EXECUTED
        req.decided_by = actor
        req.decided_at = datetime.now(timezone.utc)
        self._log(req, "approval_executed", "tool executed after approval")
        self._requests.pop(request_id, None)
        return req

    def _get_open(self, request_id: str) -> ApprovalRequest:
        req = self._requests.get(request_id)
        if not req:
            raise KeyError(request_id)
        if req.state not in (ApprovalState.REQUESTED, ApprovalState.PENDING_TIMEOUT):
            raise ValueError(f"request already finalized: {req.state}")
        return req

    def _finalize(
        self,
        req: ApprovalRequest,
        new_state: ApprovalState,
        actor: str,
        reason: str,
    ) -> None:
        req.state = new_state
        req.decided_by = actor
        req.decided_at = datetime.now(timezone.utc)
        req.decision_reason = reason
        self._cancel_timeout(req.request_id)
        self._log(req, f"approval_{new_state.value}", reason)
        if new_state in (ApprovalState.REJECTED, ApprovalState.CANCELLED):
            self._requests.pop(req.request_id, None)

    def _cancel_timeout(self, request_id: str) -> None:
        task = self._timeouts.pop(request_id, None)
        if task:
            task.cancel()

    def _log(self, req: ApprovalRequest, action: str, reason: str) -> None:
        self.event_writer.write(
            run_id=req.run_id,
            event_type=EventType.APPROVAL,
            payload=req.model_dump(mode="json"),
            source="approval_service",
            actor=req.decided_by or req.requested_by,
            correlation_id=req.correlation_id,
        )
        self.audit_log.append(
            run_id=req.run_id,
            actor=req.decided_by or req.requested_by,
            action=action,
            target=req.tool_name,
            params=req.params,
            reason=reason,
            correlation_id=req.correlation_id,
        )

    def list_pending(self) -> list[ApprovalRequest]:
        return [r for r in self._requests.values() if r.state == ApprovalState.REQUESTED]

    def find_approved(
        self,
        run_id: str,
        tool_name: str,
        params: dict[str, Any],
        correlation_id: str,
    ) -> ApprovalRequest | None:
        for req in self._requests.values():
            if (
                req.run_id == run_id
                and req.tool_name == tool_name
                and req.params == params
                and req.correlation_id == correlation_id
                and req.state == ApprovalState.APPROVED
            ):
                return req
        return None

    def cancel_all_pending(self, safe_default: str | None = None) -> list[ApprovalRequest]:
        """Cancel all pending requests on startup/shutdown. Phase 1 safety fallback."""
        cancelled: list[ApprovalRequest] = []
        for req in list(self._requests.values()):
            if req.state != ApprovalState.REQUESTED:
                continue
            default = safe_default or req.safe_default
            if default in ("cancel", "reject"):
                self._finalize(req, ApprovalState.CANCELLED, "system", f"cancel_all_pending safe_default={default}")
            else:
                req.state = ApprovalState.PENDING_TIMEOUT
                self._log(req, "approval_pending_timeout", "cancel_all_pending hold")
            cancelled.append(req)
        return cancelled

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        return self._requests.get(request_id)
