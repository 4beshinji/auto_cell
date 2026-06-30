"""ALCOA-lite audit log tests."""

from __future__ import annotations

import json

from auto_cell.audit.audit_log import AuditLog


def test_hash_chain_integrity(tmp_path):
    log = AuditLog(tmp_path)
    log.append("run_001", "system", "tool_executed", "set_perfusion_rate", {"vvd": 3.0}, "glucose low", "corr_1")
    log.append("run_001", "user:tanaka", "approval_approved", "set_perfusion_rate", {"vvd": 8.5}, "confirmed", "corr_1")
    assert log.verify("run_001") == []


def test_tamper_detection(tmp_path):
    log = AuditLog(tmp_path)
    log.append("run_001", "system", "tool_executed", "set_perfusion_rate", {"vvd": 3.0}, "glucose low", "corr_1")
    path = log._path("run_001")
    lines = path.read_text().splitlines()
    bad = json.loads(lines[0])
    bad["params"]["vvd"] = 99.0
    lines[0] = json.dumps(bad)
    path.write_text("\n".join(lines) + "\n")
    assert len(log.verify("run_001")) >= 1


def test_empty_run_verifies(tmp_path):
    log = AuditLog(tmp_path)
    assert log.verify("empty_run") == []


def test_tamper_prev_hash(tmp_path):
    log = AuditLog(tmp_path)
    log.append("run_001", "system", "tool_executed", "set_perfusion_rate", {"vvd": 3.0}, "glucose low", "corr_1")
    log.append("run_001", "user:tanaka", "approval_approved", "set_perfusion_rate", {"vvd": 8.5}, "confirmed", "corr_1")
    path = log._path("run_001")
    lines = path.read_text().splitlines()
    second = json.loads(lines[1])
    second["prev_hash"] = "0" * 64
    lines[1] = json.dumps(second)
    path.write_text("\n".join(lines) + "\n")
    broken = log.verify("run_001")
    assert any("prev_hash mismatch" in b for b in broken)
