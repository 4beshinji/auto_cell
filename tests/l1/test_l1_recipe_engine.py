"""Tests for the integrated RecipeEngine."""

from __future__ import annotations

import pytest

from auto_cell.l1.recipe_engine import RecipeEngine
from auto_cell.plugins.cell_culture.environment import CellCultureEnv


def make_env(**kwargs):
    defaults = dict(
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
    defaults.update(kwargs)
    return CellCultureEnv(**defaults)


@pytest.fixture
def engine():
    return RecipeEngine.from_files(
        "config/recipes/manstein_phase1.yaml",
        "config/recipes/manstein_rules.yaml",
        suppression_defaults={},
    )


def test_seed_state_entry_actions(engine):
    env = make_env()
    result = engine.step(1, 0.0, env)
    assert result.state_id == "seed"
    tools = [c.action.tool for c in result.candidates]
    assert "set_gas_setpoint" in tools
    assert "set_agitation_rpm" in tools


def test_seed_to_perfusion_ramp_transition(engine):
    env = make_env()
    result = engine.step(1, 0.6, env)
    assert result.state_id == "perfusion_ramp"


def test_ramp_perfusion_scheduled(engine):
    env = make_env()
    engine.step(1, 0.6, env)  # enter ramp
    result = engine.step(2, 24.0, env)
    assert result.state_id == "perfusion_ramp"
    assert any(a.tool == "set_perfusion_rate" for a in result.executed)


def test_passage_ready_requires_approval(engine):
    env = make_env(vcd=36.0e6)
    engine.step(1, 0.6, env)  # seed -> ramp
    result = engine.step(2, 120.0, env)
    assert result.state_id == "passage_ready"
    assert any(a.tool == "notify" for a in result.executed)


def test_determinism(engine):
    env = make_env(glucose_mM=1.5)
    r1 = engine.step(1, 10.0, env)
    engine2 = RecipeEngine.from_files(
        "config/recipes/manstein_phase1.yaml",
        "config/recipes/manstein_rules.yaml",
        suppression_defaults={},
    )
    r2 = engine2.step(1, 10.0, env)
    assert [c.action.model_dump() for c in r1.candidates] == [c.action.model_dump() for c in r2.candidates]
