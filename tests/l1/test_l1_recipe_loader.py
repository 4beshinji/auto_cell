"""Tests for DSL loading, validation, and value_ref resolution."""

from __future__ import annotations


from auto_cell.l1.recipe_loader import ConditionEvaluator, load_recipe, load_rules
from auto_cell.l1.types import Context, SensorCondition


def test_load_manstein_recipe():
    recipe = load_recipe("config/recipes/manstein_phase1.yaml")
    assert recipe.id == "manstein_phase1"
    assert "seed" in recipe.states
    assert recipe.initial_state == "seed"


def test_load_manstein_rules():
    rules = load_rules("config/recipes/manstein_rules.yaml")
    assert any(r.id == "glucose_low_bolus" for r in rules)


def test_sensor_condition_op_alias():
    data = {"sensor": "glucose_mM", "le": 1.8, "for_minutes": 5.0}
    cond = SensorCondition.model_validate(data)
    assert cond.op == "le"
    assert cond.value == 1.8


def test_context_resolves_refs():
    recipe = load_recipe("config/recipes/manstein_phase1.yaml")
    ctx = Context(recipe=recipe, elapsed_hours=0.0, state_id="seed")
    assert ctx.resolve("variables.target_vcd.value") == 35.0e6
    assert ctx.resolve("setpoints.ph.value") == 7.1
    assert ctx.resolve("cycle.elapsed_hours") == 0.0
    assert ctx.resolve("cycle.state_id") == "seed"


def test_condition_evaluator_sensor():
    class FakeEnv:
        glucose_mM = 1.5
        vcd = 1.0e6

    recipe = load_recipe("config/recipes/manstein_phase1.yaml")
    ctx = Context(recipe=recipe, env=FakeEnv(), elapsed_hours=10.0, state_id="perfusion_ramp")
    eval_ = ConditionEvaluator(ctx)

    assert eval_.evaluate(SensorCondition(sensor="glucose_mM", op="le", value=1.8))
    assert not eval_.evaluate(SensorCondition(sensor="glucose_mM", op="ge", value=5.0))
    assert eval_.evaluate(SensorCondition(sensor="vcd", op="ge", value="variables.seed_density.value"))
