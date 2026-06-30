"""Tests for the HMI dashboard HTML UI."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from auto_cell.audit.audit_log import AuditLog
from auto_cell.audit.event_store import EventWriter
from auto_cell.hmi.approval_api import Services, app
from auto_cell.hmi.approval_matrix import ApprovalMatrix
from auto_cell.hmi.approval_service import ApprovalService
from auto_cell.hmi.dashboard_service import DashboardService
from auto_cell.schemas.audit_events import TelemetryPayload


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    ew = EventWriter(tmp_path / "events")
    al = AuditLog(tmp_path / "audit")
    matrix = ApprovalMatrix(Path(__file__).parent.parent / "config" / "approval_matrix.yaml")
    svc = ApprovalService(ew, al, matrix)
    services = Services.__new__(Services)
    services.event_writer = ew
    services.audit_log = al
    services.matrix = matrix
    services.approval_service = svc
    services.dashboard = DashboardService(ew)

    monkeypatch.setattr("auto_cell.hmi.approval_api._services", services)

    with TestClient(app) as c:
        yield c


def test_dashboard_page_renders(client):
    resp = client.get("/hmi")
    assert resp.status_code == 200
    text = resp.text
    assert "<title>auto_cell HMI Dashboard</title>" in text
    assert '/hmi/static/css/dashboard.css' in text
    assert '/hmi/static/js/dashboard.js' in text
    assert 'id="run-select"' in text
    assert 'id="approvals-list"' in text


def test_static_assets_served(client):
    for path in ["/hmi/static/css/dashboard.css", "/hmi/static/js/dashboard.js"]:
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert resp.headers.get("content-type") != "text/html; charset=utf-8"


def test_list_runs_empty(client):
    resp = client.get("/hmi/runs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_runs_returns_run_with_events(client):
    svc = get_services_from_client(client)
    svc.dashboard.write_telemetry("run_hmi_001", TelemetryPayload(channel="vcd", value=1.0e6, unit="cells/mL"))

    resp = client.get("/hmi/runs")
    assert resp.status_code == 200
    assert resp.json() == ["run_hmi_001"]


def test_dashboard_status_for_run(client):
    svc = get_services_from_client(client)
    svc.dashboard.write_telemetry("run_hmi_002", TelemetryPayload(channel="vcd", value=2.0e6, unit="cells/mL"))
    svc.dashboard.write_telemetry("run_hmi_002", TelemetryPayload(channel="phase", value="growth", unit=None))

    resp = client.get("/hmi/runs/run_hmi_002/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == "run_hmi_002"
    assert data["phase"] == "growth"
    assert data["cpp"]["vcd"] == 2.0e6


def test_pending_approval_visible_to_ui(client):
    svc = get_services_from_client(client)
    req = asyncio.run(
        svc.approval_service.request(
            run_id="run_hmi_003",
            tool_name="trigger_passage",
            params={"target_vcd": 35e6},
            requested_by="system",
            timeout_sec=600,
            safe_default="cancel",
            correlation_id="corr_hmi_1",
            reason="VCD target predicted",
        )
    )

    resp = client.get("/hmi/approvals/pending")
    assert resp.status_code == 200
    items = resp.json()
    assert any(item["request_id"] == req.request_id for item in items)

    # UI page should include container the JS renders into.
    resp = client.get("/hmi")
    assert 'id="approvals-list"' in resp.text


def get_services_from_client(client):
    """Access the patched global services instance used by the app."""
    from auto_cell.hmi.approval_api import _services

    assert _services is not None
    return _services
