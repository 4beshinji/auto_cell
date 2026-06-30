"""Approval flow E2E tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from auto_cell.audit.audit_log import AuditLog
from auto_cell.audit.event_store import EventWriter
from auto_cell.hmi.approval_matrix import ApprovalMatrix
from auto_cell.hmi.approval_service import ApprovalService, ApprovalState


@pytest.fixture
def services(tmp_path: Path):
    ew = EventWriter(tmp_path / "events")
    al = AuditLog(tmp_path / "audit")
    matrix = ApprovalMatrix(Path(__file__).parent.parent / "config" / "approval_matrix.yaml")
    svc = ApprovalService(ew, al, matrix)
    return svc, ew, al


@pytest.mark.asyncio
async def test_request_approve_execute(services):
    svc, ew, al = services
    req = await svc.request(
        run_id="run_001",
        tool_name="set_perfusion_rate",
        params={"vvd": 8.5},
        requested_by="system",
        timeout_sec=600,
        safe_default="cancel",
        correlation_id="corr_1",
        reason="lactate high, need higher perfusion",
    )
    assert req.state == ApprovalState.REQUESTED

    approved = svc.approve(req.request_id, "user:tanaka", "confirmed by shift leader")
    assert approved.state == ApprovalState.APPROVED

    executed = svc.execute(req.request_id)
    assert executed.state == ApprovalState.EXECUTED

    assert len(al.verify("run_001")) == 0


@pytest.mark.asyncio
async def test_reject_cancels(services):
    svc, ew, al = services
    req = await svc.request(
        run_id="run_001",
        tool_name="trigger_passage",
        params={},
        requested_by="system",
        timeout_sec=600,
        safe_default="cancel",
        correlation_id="corr_2",
        reason="vcd target reached",
    )
    rejected = svc.reject(req.request_id, "user:sato", "not ready for passage")
    assert rejected.state == ApprovalState.REJECTED
    assert len(al.verify("run_001")) == 0


@pytest.mark.asyncio
async def test_timeout_cancels(services):
    svc, ew, al = services
    req = await svc.request(
        run_id="run_001",
        tool_name="trigger_passage",
        params={},
        requested_by="system",
        timeout_sec=0.1,
        safe_default="cancel",
        correlation_id="corr_2",
        reason="vcd target reached",
    )
    await asyncio.sleep(0.2)
    assert req.state == ApprovalState.CANCELLED


@pytest.mark.asyncio
async def test_timeout_hold(services):
    svc, ew, al = services
    req = await svc.request(
        run_id="run_001",
        tool_name="contamination_suspected",
        params={},
        requested_by="system",
        timeout_sec=0.1,
        safe_default="hold",
        correlation_id="corr_3",
        reason="suspected contamination",
    )
    await asyncio.sleep(0.2)
    assert req.state == ApprovalState.PENDING_TIMEOUT


@pytest.mark.asyncio
async def test_double_approval_raises(services):
    svc, ew, al = services
    req = await svc.request(
        run_id="run_001",
        tool_name="set_perfusion_rate",
        params={"vvd": 8.5},
        requested_by="system",
        timeout_sec=600,
        safe_default="cancel",
        correlation_id="corr_4",
        reason="test",
    )
    svc.approve(req.request_id, "user:tanaka", "ok")
    with pytest.raises(ValueError):
        svc.approve(req.request_id, "user:tanaka", "ok again")


def test_cancel_all_pending(services):
    svc, ew, al = services
    import asyncio

    req = asyncio.run(
        svc.request(
            run_id="run_001",
            tool_name="set_perfusion_rate",
            params={"vvd": 8.5},
            requested_by="system",
            timeout_sec=600,
            safe_default="cancel",
            correlation_id="corr_5",
            reason="test",
        )
    )
    cancelled = svc.cancel_all_pending()
    assert len(cancelled) == 1
    assert req.state == ApprovalState.CANCELLED
