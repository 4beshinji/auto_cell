"""Tests for the recipe state machine."""

from __future__ import annotations

import pytest

from auto_cell.l1.recipe_loader import load_recipe
from auto_cell.l1.state_machine import RecipeStateMachine
from auto_cell.l1.types import Context


@pytest.fixture
def recipe():
    return load_recipe("config/recipes/manstein_phase1.yaml")


class EnvSeed:
    culture_age_d = 0.0
    vcd = 0.5e6


class EnvRamp:
    culture_age_d = 5.0
    vcd = 36.0e6


def test_seed_to_perfusion_ramp(recipe):
    ctx = Context(recipe=recipe, env=EnvSeed(), elapsed_hours=0.6, state_id="seed")
    sm = RecipeStateMachine(recipe, ctx)
    targets = sm.evaluate_transitions(0.6)
    assert "perfusion_ramp" in targets


def test_perfusion_ramp_to_passage_ready(recipe):
    ctx = Context(recipe=recipe, env=EnvSeed(), elapsed_hours=0.0, state_id="seed")
    sm = RecipeStateMachine(recipe, ctx)
    sm.to_state("perfusion_ramp", elapsed_hours=0.6)
    sm.context.env = EnvRamp()
    targets = sm.evaluate_transitions(120.0)
    assert "passage_ready" in targets


def test_to_state_collects_entry_actions(recipe):
    ctx = Context(recipe=recipe, env=EnvSeed(), elapsed_hours=0.0, state_id="seed")
    sm = RecipeStateMachine(recipe, ctx)
    sm.to_state("perfusion_ramp", elapsed_hours=0.6)
    assert sm.state == "perfusion_ramp"
    assert len(sm.pending_entry_actions) == 0  # perfusion_ramp has no entry actions


def test_seed_entry_actions_collected(recipe):
    ctx = Context(recipe=recipe, env=EnvSeed(), elapsed_hours=0.0, state_id="seed")
    sm = RecipeStateMachine(recipe, ctx)
    assert len(sm.pending_entry_actions) == 0
    sm.to_state("perfusion_ramp", elapsed_hours=0.6)
    # seed's on_exit is empty, perfusion_ramp entry_actions is empty
    assert sm.state == "perfusion_ramp"


def test_timeout_returns_hold(recipe):
    ctx = Context(recipe=recipe, env=EnvSeed(), elapsed_hours=0.0, state_id="seed")
    sm = RecipeStateMachine(recipe, ctx)
    sm.to_state("perfusion_ramp", elapsed_hours=0.6)
    assert sm.apply_timeout(169.0) == "hold"
