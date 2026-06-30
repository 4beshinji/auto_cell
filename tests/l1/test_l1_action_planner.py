"""Tests for action planner normalization, validation, and ordering."""

from __future__ import annotations

import pytest

from auto_cell.l1.action_planner import ActionPlanner
from auto_cell.l1.types import ActionCandidate, Context, Recipe, ToolCall
from auto_cell.plugins.cell_culture.environment import CellCultureEnv


@pytest.fixture
def env():
    return CellCultureEnv(
        vcd=1.0e6,
        viability_pct=97.0,
        glucose_mM=3.0,
        lactate_mM=5.0,
        glutamine_mM=2.0,
        ph=7.1,
        do_pct=40.0,
        temp_c=37.0,
        osmolality_mOsm_kg=300.0,
        agitation_rpm=80.0,
        perfusion_rate_vvd=0.0,
    )


@pytest.fixture
def recipe():
    return Recipe(
        id="test",
        version="0.1.0",
        title="test",
        culture_unit_id="cu_test",
        initial_state="seed",
        setpoints={"agitation": {"value": 80, "unit": "rpm"}},
        variables={
            "max_perfusion": {"value": 7.0, "unit": "vvd"},
            "perfusion_ramp_start_h": {"value": 0.5, "unit": "h"},
            "perfusion_ramp_end_h": {"value": 120.0, "unit": "h"},
        },
        states={},
    )


def test_normalize_set_perfusion_rate(env, recipe):
    planner = ActionPlanner()
    ctx = Context(recipe=recipe, env=env, elapsed_hours=10.0, state_id="seed")
    candidates = [
        ActionCandidate(
            source="rule",
            priority="P1",
            action=ToolCall(tool="set_perfusion_rate", args={"rate_ref": "variables.max_perfusion.value"}),
            reason="test",
        )
    ]
    executed, _, _ = planner.plan(candidates, env, "seed", ctx)
    assert executed
    assert executed[0].args["vvd"] == 7.0


def test_ramp_perfusion_expansion(env, recipe):
    planner = ActionPlanner()
    ctx = Context(recipe=recipe, env=env, elapsed_hours=60.0, state_id="perfusion_ramp")
    candidates = [
        ActionCandidate(
            source="recipe",
            priority="P2",
            action=ToolCall(
                tool="ramp_perfusion",
                args={
                    "start_h_ref": "variables.perfusion_ramp_start_h.value",
                    "end_h_ref": "variables.perfusion_ramp_end_h.value",
                    "start_rate": 0.0,
                    "end_rate_ref": "variables.max_perfusion.value",
                },
            ),
            reason="scheduled",
        )
    ]
    executed, _, _ = planner.plan(candidates, env, "perfusion_ramp", ctx)
    assert executed
    assert executed[0].tool == "set_perfusion_rate"
    # mid-ramp at 60h between 0.5 and 120 -> roughly 3.5 vvd
    assert 3.0 < executed[0].args["vvd"] < 4.0


def test_action_ordering(env, recipe):
    planner = ActionPlanner()
    ctx = Context(recipe=recipe, env=env, elapsed_hours=10.0, state_id="seed")
    candidates = [
        ActionCandidate(
            source="rule", priority="P2", action=ToolCall(tool="feed", args={"media_id": "x", "volume_ml": 1.0}), reason="feed"
        ),
        ActionCandidate(
            source="rule", priority="P2", action=ToolCall(tool="set_perfusion_rate", args={"vvd": 1.0}), reason="perf"
        ),
        ActionCandidate(
            source="rule", priority="P2", action=ToolCall(tool="exchange_media", args={"media_id": "x", "volume_ml": 1.0}), reason="ex"
        ),
    ]
    executed, _, _ = planner.plan(candidates, env, "seed", ctx)
    tools = [a.tool for a in executed]
    assert tools == ["exchange_media", "set_perfusion_rate", "feed"]


def test_rejected_missing_rock_inhibitor(env, recipe):
    planner = ActionPlanner()
    ctx = Context(recipe=recipe, env=env, elapsed_hours=10.0, state_id="seed")
    candidates = [
        ActionCandidate(
            source="rule", priority="P2", action=ToolCall(tool="trigger_passage", args={"method": "dissociate"}), reason="bad"
        )
    ]
    executed, rejected, _ = planner.plan(candidates, env, "seed", ctx)
    assert not executed
    assert rejected
