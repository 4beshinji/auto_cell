"""Wave 2 reliability and security hardening tests."""

from __future__ import annotations

import json

import pytest

from auto_cell._utils import validate_run_id
from auto_cell.audit.audit_log import AuditLog
from auto_cell.audit.event_store import EventWriter
from auto_cell.hmi.approval_service import ApprovalService, ApprovalState


def test_validate_run_id_rejects_path_traversal():
    with pytest.raises(ValueError):
        validate_run_id("../etc/passwd")
    with pytest.raises(ValueError):
        validate_run_id("run/../other")
    with pytest.raises(ValueError):
        validate_run_id("run id")
    assert validate_run_id("run_001") == "run_001"
    assert validate_run_id("run-001.test") == "run-001.test"


def test_audit_log_restores_hash_chain_after_restart(tmp_path):
    log1 = AuditLog(tmp_path)
    log1.append("run_001", "system", "tool_executed", "set_perfusion_rate", {"vvd": 3.0}, "glucose low", "corr_1")
    log1.append("run_001", "user:tanaka", "approval_approved", "set_perfusion_rate", {"vvd": 8.5}, "confirmed", "corr_1")

    # Simulate process restart: new AuditLog instance reads existing file.
    log2 = AuditLog(tmp_path)
    log2.append("run_001", "system", "tool_executed", "set_perfusion_rate", {"vvd": 9.0}, "next step", "corr_2")

    broken = log2.verify("run_001")
    assert broken == []

    path = log2._path("run_001")
    lines = path.read_text().splitlines()
    assert len(lines) == 3
    seqs = [json.loads(line)["seq"] for line in lines]
    assert seqs == [1, 2, 3]


def test_event_writer_loads_multiple_days(tmp_path):
    ew = EventWriter(tmp_path)
    run_dir = tmp_path / "run_001"
    run_dir.mkdir(parents=True)

    day1 = {
        "header": {
            "event_id": "e1",
            "schema_version": "1.0",
            "run_id": "run_001",
            "correlation_id": None,
            "parent_event_id": None,
            "timestamp": "2025-01-01T00:00:00Z",
            "source": "test",
            "actor": "system",
            "event_type": "telemetry",
        },
        "payload": {"channel": "vcd", "value": 1.0},
    }
    day2 = {
        "header": {
            "event_id": "e2",
            "schema_version": "1.0",
            "run_id": "run_001",
            "correlation_id": None,
            "parent_event_id": None,
            "timestamp": "2025-01-02T00:00:00Z",
            "source": "test",
            "actor": "system",
            "event_type": "telemetry",
        },
        "payload": {"channel": "vcd", "value": 2.0},
    }
    (run_dir / "20250101.jsonl").write_text(json.dumps(day1) + "\n")
    (run_dir / "20250102.jsonl").write_text(json.dumps(day2) + "\n")

    events = ew.load_run("run_001")
    assert len(events) == 2
    assert events[0].payload["value"] == 1.0
    assert events[1].payload["value"] == 2.0


@pytest.mark.asyncio
async def test_approval_service_executed_removes_request(tmp_path):
    ew = EventWriter(tmp_path / "events")
    al = AuditLog(tmp_path / "audit")
    svc = ApprovalService(ew, al)

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

    svc.approve(req.request_id, "user:tanaka", "ok")
    assert req.request_id in svc._requests
    assert svc._requests[req.request_id].state == ApprovalState.APPROVED

    svc.execute(req.request_id)
    assert req.request_id not in svc._requests
    assert req.state == ApprovalState.EXECUTED
