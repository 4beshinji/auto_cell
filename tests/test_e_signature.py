"""Electronic signature and staff independence tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from auto_cell.audit.audit_log import AuditLog
from auto_cell.audit.event_store import EventWriter
from auto_cell.auth.db import UserDB
from auto_cell.auth.models import Role, UserCreate
from auto_cell.hmi.approval_matrix import ApprovalMatrix
from auto_cell.hmi.approval_models import ApprovalState
from auto_cell.hmi.approval_service import ApprovalService


@pytest.fixture
def services(tmp_path: Path):
    ew = EventWriter(tmp_path / "events")
    al = AuditLog(tmp_path / "audit")
    matrix = ApprovalMatrix(Path(__file__).parent.parent / "config" / "approval_matrix.yaml")
    user_db = UserDB(tmp_path / "auth" / "users.db")
    requester = user_db.create_user(
        UserCreate(
            username="requester1",
            full_name="Requester One",
            password="password123",
            pin="1234",
            role=Role.OPERATOR,
        )
    )
    approver = user_db.create_user(
        UserCreate(
            username="approver1",
            full_name="Approver One",
            password="password123",
            pin="5678",
            role=Role.OPERATOR,
        )
    )
    svc = ApprovalService(ew, al, matrix, user_db=user_db)
    return svc, ew, al, requester, approver


@pytest.mark.asyncio
async def test_approve_requires_pin_and_meaning(services):
    svc, ew, al, requester, approver = services
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

    with pytest.raises(ValueError, match="meaning_of_signature"):
        svc.approve(req.request_id, approver, "5678", "ok", "")
    with pytest.raises(ValueError, match="invalid pin"):
        svc.approve(req.request_id, approver, "0000", "ok", "reviewed and approved")

    approved = svc.approve(req.request_id, approver, "5678", "ok", "reviewed and approved")
    assert approved.state == ApprovalState.APPROVED
    assert approved.meaning_of_signature == "reviewed and approved"


@pytest.mark.asyncio
async def test_approver_must_differ_from_requester(services):
    svc, ew, al, requester, approver = services
    req = await svc.request(
        run_id="run_001",
        tool_name="set_perfusion_rate",
        params={"vvd": 8.5},
        requested_by=requester.user_id,
        timeout_sec=600,
        safe_default="cancel",
        correlation_id="corr_2",
        reason="test",
    )

    with pytest.raises(ValueError, match="approver must differ from requester"):
        svc.approve(req.request_id, requester, "1234", "ok", "reviewed and approved")

    approved = svc.approve(req.request_id, approver, "5678", "ok", "reviewed and approved")
    assert approved.state == ApprovalState.APPROVED


@pytest.mark.asyncio
async def test_signature_recorded_in_audit_log(services):
    svc, ew, al, requester, approver = services
    req = await svc.request(
        run_id="run_001",
        tool_name="set_perfusion_rate",
        params={"vvd": 8.5},
        requested_by="system",
        timeout_sec=600,
        safe_default="cancel",
        correlation_id="corr_3",
        reason="test",
    )
    svc.approve(req.request_id, approver, "5678", "confirmed", "reviewed and approved")

    events = ew.load_run("run_001")
    approval_events = [e for e in events if e.header.event_type.value == "approval"]
    assert len(approval_events) >= 1
    payload = approval_events[-1].payload
    assert payload.get("decided_by") == approver.user_id
    assert payload.get("meaning_of_signature") == "reviewed and approved"

    assert len(al.verify("run_001")) == 0
