"Approval state machine, queue, and timeout handling."

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from auto_cell.audit.audit_log import AuditLog
from auto_cell.audit.event_store import EventWriter
from auto_cell.auth.db import UserDB
from auto_cell.auth.models import UserInDB
from auto_cell.hmi.approval_matrix import ApprovalMatrix
from auto_cell.hmi.approval_models import ApprovalRequest, ApprovalState
from auto_cell.hmi.approval_store import ApprovalStore, InMemoryApprovalStore
from auto_cell.schemas.audit_events import EventType


class ApprovalService:
    def __init__(
        self,
        event_writer: EventWriter,
        audit_log: AuditLog,
        matrix: ApprovalMatrix | None = None,
        store: ApprovalStore | None = None,
        user_db: UserDB | None = None,
    ):
        self._store = store or InMemoryApprovalStore()
        self._timeouts: dict[str, asyncio.Task[Any]] = {}
        self.event_writer = event_writer
        self.audit_log = audit_log
        self.matrix = matrix
        self.user_db = user_db

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
        self._store.put(req)
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
        req = self._store.get(request_id)
        if not req or req.state != ApprovalState.REQUESTED:
            return
        if req.safe_default in ("cancel", "reject"):
            req.state = ApprovalState.PENDING_TIMEOUT
            self._finalize(req, ApprovalState.CANCELLED, "system", f"timeout safe_default={req.safe_default}")
        elif req.safe_default == "hold":
            req.state = ApprovalState.PENDING_TIMEOUT
            self._log(req, "approval_pending_timeout", "awaiting human decision beyond timeout")

    def approve(
        self,
        request_id: str,
        user: UserInDB,
        pin: str,
        reason: str,
        meaning_of_signature: str,
    ) -> ApprovalRequest:
        self._verify_signature(user, pin, meaning_of_signature)
        req = self._get_open(request_id)
        if req.requested_by == user.user_id:
            raise ValueError("approver must differ from requester")
        req.meaning_of_signature = meaning_of_signature
        self._finalize(req, ApprovalState.APPROVED, user.user_id, reason)
        return req

    def reject(
        self,
        request_id: str,
        user: UserInDB,
        pin: str,
        reason: str,
        meaning_of_signature: str,
    ) -> ApprovalRequest:
        self._verify_signature(user, pin, meaning_of_signature)
        req = self._get_open(request_id)
        if req.requested_by == user.user_id:
            raise ValueError("approver must differ from requester")
        req.meaning_of_signature = meaning_of_signature
        self._finalize(req, ApprovalState.REJECTED, user.user_id, reason)
        return req

    def _verify_signature(
        self,
        user: UserInDB,
        pin: str,
        meaning_of_signature: str,
    ) -> None:
        if not meaning_of_signature or not meaning_of_signature.strip():
            raise ValueError("meaning_of_signature is required")
        if not pin or not pin.strip():
            raise ValueError("pin is required")
        if self.user_db is None:
            raise RuntimeError("user_db is not configured")
        if not self.user_db.verify_pin(pin, user):
            raise ValueError("invalid pin")

    def execute(self, request_id: str, actor: str = "system") -> ApprovalRequest:
        req = self._store.get(request_id)
        if not req or req.state != ApprovalState.APPROVED:
            raise ValueError("request must be approved before execute")
        req.state = ApprovalState.EXECUTED
        req.decided_by = actor
        req.decided_at = datetime.now(timezone.utc)
        self._store.put(req)
        self._log(req, "approval_executed", "tool executed after approval")
        self._store.delete(req.request_id)
        return req

    def _get_open(self, request_id: str) -> ApprovalRequest:
        req = self._store.get(request_id)
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
        self._store.put(req)
        self._log(req, f"approval_{new_state.value}", reason)
        if new_state in (ApprovalState.REJECTED, ApprovalState.CANCELLED):
            self._store.delete(req.request_id)

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
        return self._store.list_pending()

    def find_approved(
        self,
        run_id: str,
        tool_name: str,
        params: dict[str, Any],
        correlation_id: str,
    ) -> ApprovalRequest | None:
        return self._store.find_approved(run_id, tool_name, params, correlation_id)

    def cancel_all_pending(self, safe_default: str | None = None) -> list[ApprovalRequest]:
        """Cancel all pending requests on startup/shutdown. Phase 1 safety fallback."""
        cancelled: list[ApprovalRequest] = []
        for req in self._store.list_all():
            if req.state != ApprovalState.REQUESTED:
                continue
            default = safe_default or req.safe_default
            if default in ("cancel", "reject"):
                self._finalize(req, ApprovalState.CANCELLED, "system", f"cancel_all_pending safe_default={default}")
            else:
                req.state = ApprovalState.PENDING_TIMEOUT
                self._store.put(req)
                self._log(req, "approval_pending_timeout", "cancel_all_pending hold")
            cancelled.append(req)
        return cancelled

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        return self._store.get(request_id)
