"""Side-effect tool wrapper with contextvars and approval integration."""

from __future__ import annotations

import contextvars
import uuid
from collections.abc import Awaitable, Callable
from contextlib import contextmanager
from typing import Any

from auto_cell.audit.audit_log import AuditLog
from auto_cell.audit.event_store import EventWriter
from auto_cell.hmi.approval_matrix import ApprovalMatrix
from auto_cell.hmi.approval_service import ApprovalService, ApprovalState
from auto_cell.schemas.audit_events import EventType

_run_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("run_id", default=None)
_actor_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("actor", default="system")
_corr_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("correlation_id", default=None)
_reason_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("reason", default="")


class ApprovalRequiredError(Exception):
    def __init__(self, request: Any):
        self.request = request


class ToolNotFoundError(Exception):
    pass


class ToolExecutor:
    def __init__(
        self,
        event_writer: EventWriter,
        audit_log: AuditLog,
        approval_service: ApprovalService,
        matrix: ApprovalMatrix,
        handlers: dict[str, Callable[..., Awaitable[dict[str, Any]]]],
    ):
        self.event_writer = event_writer
        self.audit_log = audit_log
        self.approval_service = approval_service
        self.matrix = matrix
        self.handlers = handlers

    async def execute(
        self,
        tool_name: str,
        params: dict[str, Any],
        *,
        reason: str | None = None,
    ) -> dict[str, Any]:
        run_id = _run_id_ctx.get()
        if run_id is None:
            raise RuntimeError("run_id context variable is not set")
        actor = _actor_ctx.get()
        correlation_id = _corr_ctx.get() or str(uuid.uuid4())
        reason = reason or _reason_ctx.get() or "no reason provided"

        handler = self.handlers.get(tool_name)
        if handler is None:
            raise ToolNotFoundError(f"Tool not found: {tool_name}")

        decision = self.matrix.decide(tool_name, params, run_context={"run_id": run_id})
        approved_request = None
        if decision.requires_approval:
            existing = self.approval_service.find_approved(run_id, tool_name, params, correlation_id)
            if existing is not None:
                req = existing
                approved_request = req
            else:
                req = await self.approval_service.request(
                    run_id=run_id,
                    tool_name=tool_name,
                    params=params,
                    requested_by=actor,
                    timeout_sec=decision.timeout_sec,
                    safe_default=decision.safe_default,
                    correlation_id=correlation_id,
                    reason=reason,
                )
            if req.state != ApprovalState.APPROVED:
                raise ApprovalRequiredError(req)

        evt = self.event_writer.write(
            run_id=run_id,
            event_type=EventType.TOOL_EXEC,
            payload={"tool_name": tool_name, "params": params, "status": "started"},
            source="tool_executor",
            actor=actor,
            correlation_id=correlation_id,
        )

        try:
            result = await handler(**params)
        except Exception as exc:
            self.event_writer.write(
                run_id=run_id,
                event_type=EventType.TOOL_EXEC,
                payload={"tool_name": tool_name, "params": params, "status": "failed", "error": str(exc)},
                source="tool_executor",
                actor=actor,
                correlation_id=correlation_id,
                parent_event_id=evt.header.event_id,
            )
            self.audit_log.append(
                run_id=run_id,
                actor=actor,
                action="tool_execution_failed",
                target=tool_name,
                params=params,
                reason=str(exc),
                correlation_id=correlation_id,
            )
            raise

        if approved_request is not None:
            self.approval_service.execute(approved_request.request_id, actor)

        self.audit_log.append(
            run_id=run_id,
            actor=actor,
            action="tool_executed",
            target=tool_name,
            params=params,
            reason=reason,
            correlation_id=correlation_id,
        )
        self.event_writer.write(
            run_id=run_id,
            event_type=EventType.TOOL_EXEC,
            payload={"tool_name": tool_name, "params": params, "status": "completed", "result": result},
            source="tool_executor",
            actor=actor,
            correlation_id=correlation_id,
            parent_event_id=evt.header.event_id,
        )
        return result


@contextmanager
def execution_context(
    run_id: str,
    actor: str,
    correlation_id: str | None = None,
    reason: str = "",
):
    ctx_vars: list[contextvars.ContextVar[Any]] = [
        _run_id_ctx,
        _actor_ctx,
        _corr_ctx,
        _reason_ctx,
    ]
    values = (run_id, actor, correlation_id, reason)
    tokens: list[contextvars.Token[Any]] = [
        ctx.set(value) for ctx, value in zip(ctx_vars, values)
    ]
    try:
        yield
    finally:
        for ctx, tok in zip(ctx_vars, tokens):
            ctx.reset(tok)
