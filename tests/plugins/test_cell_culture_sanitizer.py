"""Tests for tool-call sanitizer."""

from datetime import datetime, timezone

from typing import Any

from auto_cell.plugins.cell_culture.environment import CellCultureEnv
from auto_cell.plugins.cell_culture.sanitizer import validate_tool_call


def _dummy_env(**kwargs: Any) -> CellCultureEnv:
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


def test_perfusion_within_envelope_accepted():
    env = _dummy_env()
    result, reason = validate_tool_call(env, "set_perfusion_rate", {"vvd": 3.0})
    assert result == "accepted"


def test_perfusion_outside_envelope_requires_approval():
    env = _dummy_env()
    result, reason = validate_tool_call(env, "set_perfusion_rate", {"vvd": 8.0})
    assert result == "approval_required"


def test_perfusion_ramp_limit_rejected():
    env = _dummy_env()
    env.last_perfusion_rate_vvd = 1.0
    env.last_setpoint_at = datetime.now(timezone.utc)  # 0 hours delta
    result, reason = validate_tool_call(env, "set_perfusion_rate", {"vvd": 2.0})
    assert result == "rejected"
    assert "ramp" in reason.lower()


def test_passage_without_rock_inhibitor_rejected():
    env = _dummy_env()
    result, reason = validate_tool_call(env, "trigger_passage", {"method": "dissociate", "add_rock_inhibitor": False})
    assert result == "rejected"
