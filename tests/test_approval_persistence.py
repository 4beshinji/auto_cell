"""Approval request persistence tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from auto_cell.audit.audit_log import AuditLog
from auto_cell.audit.event_store import EventWriter
from auto_cell.hmi.approval_matrix import ApprovalMatrix
from auto_cell.hmi.approval_models import ApprovalState
from auto_cell.hmi.approval_service import ApprovalService
from auto_cell.hmi.approval_store import InMemoryApprovalStore, SqliteApprovalStore


@pytest.fixture
def base(tmp_path: Path):
    ew = EventWriter(tmp_path / "events")
    al = AuditLog(tmp_path / "audit")
    matrix = ApprovalMatrix(Path(__file__).parent.parent / "config" / "approval_matrix.yaml")
    return ew, al, matrix


@pytest.mark.asyncio
async def test_in_memory_store_keeps_requests(base):
    ew, al, matrix = base
    store = InMemoryApprovalStore()
    svc = ApprovalService(ew, al, matrix, store=store)

    req = await svc.request(
        run_id="run_001",
        tool_name="set_perfusion_rate",
        params={"vvd": 8.5},
        requested_by="system",
        timeout_sec=600,
        safe_default="cancel",
        correlation_id="corr_1",
        reason="test",
    )
    assert store.get(req.request_id) is not None
    assert len(store.list_pending()) == 1


def test_sqlite_store_serializes_requests(tmp_path: Path, base):
    ew, al, matrix = base
    db_path = tmp_path / "approvals.db"
    store = SqliteApprovalStore(db_path)

    req = ApprovalService(ew, al, matrix, store=store).request(
        run_id="run_001",
        tool_name="set_perfusion_rate",
        params={"vvd": 8.5},
        requested_by="system",
        timeout_sec=600,
        safe_default="cancel",
        correlation_id="corr_1",
        reason="test",
    )
    req = asyncio.run(req)
    assert db_path.exists()

    # Re-open the store as if the process restarted.
    restored = SqliteApprovalStore(db_path)
    loaded = restored.get(req.request_id)
    assert loaded is not None
    assert loaded.run_id == "run_001"
    assert loaded.tool_name == "set_perfusion_rate"
    assert loaded.state == ApprovalState.REQUESTED
    assert len(restored.list_pending()) == 1


def test_sqlite_store_state_update_persisted(tmp_path: Path, base):
    ew, al, matrix = base
    db_path = tmp_path / "approvals.db"
    store = SqliteApprovalStore(db_path)
    svc = ApprovalService(ew, al, matrix, store=store)

    req = asyncio.run(
        svc.request(
            run_id="run_001",
            tool_name="set_perfusion_rate",
            params={"vvd": 8.5},
            requested_by="system",
            timeout_sec=600,
            safe_default="cancel",
            correlation_id="corr_1",
            reason="test",
        )
    )
    # Simulate state update by mutating and storing.
    req.state = ApprovalState.APPROVED
    req.decided_by = "user_1"
    store.put(req)

    restored = SqliteApprovalStore(db_path)
    loaded = restored.get(req.request_id)
    assert loaded is not None
    assert loaded.state == ApprovalState.APPROVED
    assert loaded.decided_by == "user_1"
