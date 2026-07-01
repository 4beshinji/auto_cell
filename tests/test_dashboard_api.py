"""Dashboard API smoke tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from auto_cell.audit.audit_log import AuditLog
from auto_cell.audit.event_store import EventWriter
from auto_cell.auth.db import UserDB
from auto_cell.auth.models import Role, UserCreate
from auto_cell.hmi.approval_api import Services, app, get_services
from auto_cell.hmi.approval_matrix import ApprovalMatrix
from auto_cell.hmi.approval_service import ApprovalService
from auto_cell.hmi.approval_store import SqliteApprovalStore
from auto_cell.hmi.dashboard_service import DashboardService
from auto_cell.schemas.audit_events import TelemetryPayload


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    ew = EventWriter(tmp_path / "events")
    al = AuditLog(tmp_path / "audit")
    matrix = ApprovalMatrix(Path(__file__).parent.parent / "config" / "approval_matrix.yaml")
    user_db = UserDB(tmp_path / "auth" / "users.db")
    user_db.create_user(
        UserCreate(
            username="operator1",
            full_name="Operator One",
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
            pin="1234",
            role=Role.OPERATOR,
        )
    )
    svc = ApprovalService(ew, al, matrix, store=SqliteApprovalStore(tmp_path / "approvals.db"), user_db=user_db)
    services = Services.__new__(Services)
    services.event_writer = ew
    services.audit_log = al
    services.matrix = matrix
    services.user_db = user_db
    services.approval_store = svc._store
    services.approval_service = svc
    services.dashboard = DashboardService(ew)

    monkeypatch.setattr("auto_cell.hmi.approval_api._services", services)

    with TestClient(app) as c:
        resp = c.post(
            "/hmi/auth/token",
            data={"username": "operator1", "password": "password123"},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        c.approver = approver  # type: ignore[attr-defined]
        yield c


def test_list_pending_empty(client):
    resp = client.get("/hmi/approvals/pending")
    assert resp.status_code == 200
    assert resp.json() == []


def test_approve_reject_flow(client):
    import asyncio

    svc = get_services().approval_service
    req = asyncio.run(
        svc.request(
            run_id="run_001",
            tool_name="trigger_passage",
            params={},
            requested_by="system",
            timeout_sec=600,
            safe_default="cancel",
            correlation_id="corr_1",
            reason="vcd target reached",
        )
    )

    resp = client.get(f"/hmi/approvals/{req.request_id}")
    assert resp.status_code == 200
    assert resp.json()["state"] == "requested"

    resp = client.post(
        f"/hmi/approvals/{req.request_id}/approve",
        json={
            "reason": "ok",
            "pin": "1234",
            "meaning_of_signature": "reviewed and approved",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "approved"


def test_run_status(client):
    svc = get_services()
    svc.dashboard.write_telemetry("run_002", TelemetryPayload(channel="vcd", value=1.2e6, unit="cells/mL"))
    svc.dashboard.write_telemetry("run_002", TelemetryPayload(channel="phase", value="growth", unit=None))

    resp = client.get("/hmi/runs/run_002/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == "run_002"
    assert data["phase"] == "growth"
    assert data["cpp"]["vcd"] == 1.2e6


def test_run_events_and_ebr(client):
    svc = get_services()
    svc.dashboard.write_telemetry("run_003", TelemetryPayload(channel="ph", value=7.1, unit="pH"))

    resp = client.get("/hmi/runs/run_003/events")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.get("/hmi/runs/run_003/ebr")
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == "run_003"
    assert data["summary"]["total_events"] == 1
    assert data["audit_chain_valid"] is True


def test_audit_review_recorded(client):
    svc = get_services()
    svc.dashboard.write_telemetry("run_004", TelemetryPayload(channel="ph", value=7.1, unit="pH"))

    resp = client.post(
        "/hmi/runs/run_004/audit_review",
        json={"comments": "reviewed batch record"},
    )
    assert resp.status_code == 200
    assert resp.json()["action"] == "audit_trail_reviewed"

    resp = client.get("/hmi/runs/run_004/audit_review")
    assert resp.status_code == 200
    reviews = resp.json()
    assert len(reviews) == 1
    assert reviews[0]["reason"] == "reviewed batch record"

    resp = client.get("/hmi/runs/run_004/ebr")
    assert resp.json()["audit_reviews"][0]["reason"] == "reviewed batch record"
