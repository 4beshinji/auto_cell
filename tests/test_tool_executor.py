"""Tool executor audit/approval integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from auto_cell.audit.audit_log import AuditLog
from auto_cell.audit.event_store import EventWriter
from auto_cell.audit.tool_executor import ApprovalRequiredError, ToolExecutor, execution_context
from auto_cell.auth.db import UserDB
from auto_cell.auth.models import Role, UserCreate
from auto_cell.hmi.approval_matrix import ApprovalMatrix
from auto_cell.hmi.approval_service import ApprovalService


@pytest.fixture
def services(tmp_path: Path):
    ew = EventWriter(tmp_path / "events")
    al = AuditLog(tmp_path / "audit")
    matrix = ApprovalMatrix(Path(__file__).parent.parent / "config" / "approval_matrix.yaml")
    user_db = UserDB(tmp_path / "auth" / "users.db")
    svc = ApprovalService(ew, al, matrix, user_db=user_db)
    return svc, ew, al, matrix, user_db


@pytest.fixture
def approver(services):
    _, _, _, _, user_db = services
    return user_db.create_user(
        UserCreate(
            username="approver1",
            full_name="Approver One",
            password="password123",
            pin="1234",
            role=Role.OPERATOR,
        )
    )


@pytest.mark.asyncio
async def test_envelope_auto_execute(services):
    svc, ew, al, matrix, _ = services

    async def set_perfusion_rate(vvd: float):
        return {"vvd": vvd}

    executor = ToolExecutor(ew, al, svc, matrix, {"set_perfusion_rate": set_perfusion_rate})

    with execution_context("run_001", "system", "corr_1", "glucose low"):
        result = await executor.execute("set_perfusion_rate", {"vvd": 3.0})
    assert result["vvd"] == 3.0
    assert len(al.verify("run_001")) == 0


@pytest.mark.asyncio
async def test_out_of_envelope_requires_approval(services):
    svc, ew, al, matrix, _ = services
    executor = ToolExecutor(ew, al, svc, matrix, {"set_perfusion_rate": lambda vvd: {"vvd": vvd}})

    with execution_context("run_001", "system", "corr_2", "lactate emergency"):
        with pytest.raises(ApprovalRequiredError):
            await executor.execute("set_perfusion_rate", {"vvd": 8.5})


@pytest.mark.asyncio
async def test_execute_after_approval(services, approver):
    svc, ew, al, matrix, _ = services

    async def set_perfusion_rate(vvd: float):
        return {"vvd": vvd}

    executor = ToolExecutor(ew, al, svc, matrix, {"set_perfusion_rate": set_perfusion_rate})

    with execution_context("run_001", "system", "corr_3", "lactate emergency"):
        with pytest.raises(ApprovalRequiredError) as exc_info:
            await executor.execute("set_perfusion_rate", {"vvd": 8.5})

    req = exc_info.value.request
    svc.approve(req.request_id, approver, "1234", "confirmed", "reviewed and approved")

    with execution_context("run_001", "system", "corr_3", "lactate emergency"):
        result = await executor.execute("set_perfusion_rate", {"vvd": 8.5})

    assert result["vvd"] == 8.5
    assert len(al.verify("run_001")) == 0


def test_execution_context_requires_run_id():
    executor = ToolExecutor(
        EventWriter("/tmp"),
        AuditLog("/tmp"),
        ApprovalService(EventWriter("/tmp"), AuditLog("/tmp")),
        ApprovalMatrix(Path(__file__).parent.parent / "config" / "approval_matrix.yaml"),
        {},
    )

    async def run():
        with pytest.raises(RuntimeError):
            await executor.execute("set_perfusion_rate", {"vvd": 3.0})

    import asyncio

    asyncio.run(run())
