"""Tests for the deterministic rule engine."""

from __future__ import annotations


from auto_cell.l1.rule_engine import RuleEngine
from auto_cell.l1.types import Rule, SensorCondition, ToolCall
from auto_cell.plugins.cell_culture.environment import CellCultureEnv


RULES = [
    Rule(
        id="glucose_low",
        priority="P2",
        when=SensorCondition(sensor="glucose_mM", op="le", value=1.8),
        actions=[ToolCall(tool="feed", args={"media_id": "glucose", "volume_ml": 1.0, "glucose_mM": 200.0})],
        cooldown_minutes=5.0,
    ),
    Rule(
        id="lactate_high",
        priority="P1",
        when=SensorCondition(sensor="lactate_mM", op="ge", value=35.0),
        actions=[ToolCall(tool="exchange_media", args={"media_id": "fresh", "volume_ml": 75.0})],
        cooldown_minutes=60.0,
    ),
]

RULES_WITH_FOR_MINUTES = [
    Rule(
        id="glucose_low_sustained",
        priority="P2",
        when=SensorCondition(sensor="glucose_mM", op="le", value=1.8, for_minutes=5.0),
        actions=[ToolCall(tool="feed", args={"media_id": "glucose", "volume_ml": 1.0, "glucose_mM": 200.0})],
        cooldown_minutes=0.0,
    ),
]


def test_glucose_low_fires():
    engine = RuleEngine(RULES)
    env = CellCultureEnv(
        vcd=1.0e6,
        viability_pct=97.0,
        glucose_mM=1.5,
        lactate_mM=5.0,
        glutamine_mM=2.0,
        ph=7.1,
        do_pct=40.0,
        temp_c=37.0,
        osmolality_mOsm_kg=300.0,
        agitation_rpm=80.0,
    )
    cands = engine.evaluate(env, [], elapsed_hours=24.0)
    assert any(c.action.tool == "feed" for c in cands)


def test_glucose_normal_does_not_fire():
    engine = RuleEngine(RULES)
    env = CellCultureEnv(
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
    )
    cands = engine.evaluate(env, [], elapsed_hours=24.0)
    assert not any(c.action.tool == "feed" for c in cands)


def test_priority_sorting():
    engine = RuleEngine(RULES)
    env = CellCultureEnv(
        vcd=1.0e6,
        viability_pct=97.0,
        glucose_mM=1.5,
        lactate_mM=40.0,
        glutamine_mM=2.0,
        ph=7.1,
        do_pct=40.0,
        temp_c=37.0,
        osmolality_mOsm_kg=300.0,
        agitation_rpm=80.0,
    )
    cands = engine.evaluate(env, [], elapsed_hours=24.0)
    priorities = [c.priority for c in cands]
    assert priorities == sorted(priorities, key=lambda p: ("P0", "P1", "P2", "P3").index(p))


def test_cooldown_suppresses_repeat():
    engine = RuleEngine(RULES)
    env = CellCultureEnv(
        vcd=1.0e6,
        viability_pct=97.0,
        glucose_mM=1.5,
        lactate_mM=5.0,
        glutamine_mM=2.0,
        ph=7.1,
        do_pct=40.0,
        temp_c=37.0,
        osmolality_mOsm_kg=300.0,
        agitation_rpm=80.0,
    )
    cands1 = engine.evaluate(env, [], elapsed_hours=1.0)
    assert cands1
    cands2 = engine.evaluate(env, [], elapsed_hours=1.04)  # 2.4 min < 5 min cooldown
    assert not cands2


def test_for_minutes_requires_continuous_true():
    engine = RuleEngine(RULES_WITH_FOR_MINUTES)
    env = CellCultureEnv(
        vcd=1.0e6,
        viability_pct=97.0,
        glucose_mM=1.5,
        lactate_mM=5.0,
        glutamine_mM=2.0,
        ph=7.1,
        do_pct=40.0,
        temp_c=37.0,
        osmolality_mOsm_kg=300.0,
        agitation_rpm=80.0,
    )
    # First evaluation records the moment the condition became True.
    cands1 = engine.evaluate(env, [], elapsed_hours=1.0)
    assert not cands1
    # 6 minutes later the sustained threshold is met.
    cands2 = engine.evaluate(env, [], elapsed_hours=1.1)
    assert cands2
    assert all(c.action.tool == "feed" for c in cands2)
