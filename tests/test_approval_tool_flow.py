"""Wave 3: one-shot approval and safety-gate integration tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from auto_cell.audit.audit_log import AuditLog
from auto_cell.audit.event_store import EventWriter
from auto_cell.audit.tool_executor import (
    ApprovalRequiredError,
    ToolExecutor,
    ToolNotFoundError,
    execution_context,
)
from auto_cell.auth.db import UserDB
from auto_cell.auth.models import Role, UserCreate
from auto_cell.hmi.approval_matrix import ApprovalMatrix
from auto_cell.hmi.approval_service import ApprovalService
from auto_cell.l1.cycle_executor import L1CycleExecutor
from auto_cell.l1.types import CycleResult, ToolCall
from auto_cell.plugins.cell_culture import CellCulturePlugin
from auto_cell.plugins.cell_culture.environment import CellCultureEnv
from physical_ai_core.brain.plugin_base import BrainContext


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
async def test_executor_calls_approval_service_execute_after_success(services, approver):
    svc, ew, al, matrix, _ = services

    async def set_perfusion_rate(vvd: float):
        return {"vvd": vvd}

    executor = ToolExecutor(ew, al, svc, matrix, {"set_perfusion_rate": set_perfusion_rate})

    with execution_context("run_001", "system", "corr_1", "lactate emergency"):
        with pytest.raises(ApprovalRequiredError) as exc_info:
            await executor.execute("set_perfusion_rate", {"vvd": 8.5})

    req = exc_info.value.request
    svc.approve(req.request_id, approver, "1234", "confirmed", "reviewed and approved")
    assert svc.get_request(req.request_id) is not None

    with execution_context("run_001", "system", "corr_1", "lactate emergency"):
        result = await executor.execute("set_perfusion_rate", {"vvd": 8.5})

    assert result["vvd"] == 8.5
    assert svc.get_request(req.request_id) is None


@pytest.mark.asyncio
async def test_executor_raises_tool_not_found_for_unknown_tool(services):
    svc, ew, al, matrix, _ = services
    executor = ToolExecutor(ew, al, svc, matrix, {})

    with execution_context("run_001", "system"):
        with pytest.raises(ToolNotFoundError):
            await executor.execute("unknown_tool", {"foo": "bar"})


@pytest.mark.asyncio
async def test_executor_logs_failed_event_and_audit_on_handler_error(services):
    svc, ew, al, matrix, _ = services

    async def failing_handler(volume_ml: float, purpose: str = "at-line"):
        raise RuntimeError("actuator offline")

    executor = ToolExecutor(ew, al, svc, matrix, {"take_sample": failing_handler})

    with execution_context("run_001", "system", "corr_2", "test failure logging"):
        with pytest.raises(RuntimeError, match="actuator offline"):
            await executor.execute("take_sample", {"volume_ml": 5.0})

    events = ew.load_run("run_001")
    assert any(
        e.payload.get("status") == "started" for e in events
    )
    failed_events = [
        e for e in events
        if e.payload.get("status") == "failed" and e.payload.get("error") == "actuator offline"
    ]
    assert len(failed_events) == 1
    started_event = [e for e in events if e.payload.get("status") == "started"][0]
    assert failed_events[0].header.parent_event_id == started_event.header.event_id

    records = al.verify("run_001")
    assert records == []
    audit_path = al._path("run_001")
    import json

    audit_records = [json.loads(line) for line in audit_path.read_text().splitlines() if line.strip()]
    failed_records = [
        r for r in audit_records
        if r.get("action") == "tool_execution_failed" and r.get("target") == "take_sample"
    ]
    assert len(failed_records) == 1
    assert failed_records[0].get("reason") == "actuator offline"


def _make_env(**kwargs: Any) -> CellCultureEnv:
    defaults: dict[str, Any] = {
        "vcd": 1.0e6,
        "viability_pct": 95.0,
        "glucose_mM": 5.0,
        "lactate_mM": 10.0,
        "glutamine_mM": 0.1,
        "ph": 7.1,
        "do_pct": 40.0,
        "temp_c": 37.0,
        "osmolality_mOsm_kg": 320.0,
        "agitation_rpm": 80.0,
        "perfusion_rate_vvd": 1.0,
    }
    defaults.update(kwargs)
    return CellCultureEnv(**defaults)


def _make_brain_context(env: CellCultureEnv) -> BrainContext:
    culture_unit = SimpleNamespace(
        domain_envs=SimpleNamespace(cell_culture=env),
    )
    world_model = SimpleNamespace(culture_units={"cu_001": culture_unit})
    return BrainContext(
        mcp_bridge=None,
        mqtt_client=None,
        http_session=None,
        device_registry=None,
        world_model=world_model,
        event_writer=None,
    )


def test_cell_culture_plugin_validate_rejects_extreme_setpoint():
    env = _make_env()
    plugin = CellCulturePlugin()
    plugin.on_init(_make_brain_context(env))

    allowed, reason = plugin.validate_tool_call("set_perfusion_rate", {"vvd": 3.0})
    assert allowed is True
    assert reason == ""

    rejected, reason = plugin.validate_tool_call("set_perfusion_rate", {"vvd": 100.0})
    assert rejected is False
    assert "perfusion" in reason.lower() or "envelope" in reason.lower()


def test_cell_culture_plugin_validate_requires_approval_outside_envelope():
    env = _make_env()
    plugin = CellCulturePlugin()
    plugin.on_init(_make_brain_context(env))

    allowed, reason = plugin.validate_tool_call("set_perfusion_rate", {"vvd": 8.0})
    assert allowed is False
    assert "approval" in reason.lower() or "envelope" in reason.lower() or "outside" in reason.lower()


def test_cycle_executor_updates_last_perfusion_rate_vvd():
    env = _make_env(perfusion_rate_vvd=0.0)

    class DummyEngine:
        def step(self, cycle: int, elapsed_hours: float, env: CellCultureEnv) -> CycleResult:
            return CycleResult(
                cycle=cycle,
                elapsed_hours=elapsed_hours,
                state_id="test",
                sensor_snapshot=env,
                events=[],
                candidates=[],
                executed=[ToolCall(tool="set_perfusion_rate", args={"vvd": 2.5})],
                rejected=[],
                approval_requested=[],
            )

    commands: list[str] = []
    exec_ = L1CycleExecutor(
        recipe_engine=DummyEngine(),  # type: ignore[arg-type]
        get_env=lambda: env,
        issue_command=lambda tc, _cid: commands.append(tc.tool),
        request_approval=lambda _tc, _cid: None,
        audit=lambda _r: None,
    )
    result = exec_.run_once()

    assert "set_perfusion_rate" in commands
    assert env.last_perfusion_rate_vvd == 2.5
    assert result.executed[0].args["vvd"] == 2.5
