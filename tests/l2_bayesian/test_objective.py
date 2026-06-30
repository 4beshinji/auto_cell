"""Tests for CultureObjective."""

from __future__ import annotations

from auto_cell.l2_bayesian.objective import CultureObjective, RunMetrics


def _metrics(**kwargs: float) -> RunMetrics:
    defaults: dict[str, float] = {
        "vcd_final": 35e6,
        "viability_final": 0.95,
        "pluripotency_pct": 0.92,
        "mean_aggregate_diameter_um": 250.0,
        "large_aggregate_ratio": 0.05,
        "total_run_cost": 800.0,
        "max_lactate_mm": 30.0,
        "max_osmolality_mosm": 420.0,
    }
    defaults.update(kwargs)
    return RunMetrics(**defaults)


def test_default_weights_have_expected_keys():
    obj = CultureObjective()
    assert set(obj.weights.keys()) == {
        "yield",
        "viability",
        "pluripotency",
        "aggregate_size",
        "cost",
    }


def test_perfect_run_high_score():
    obj = CultureObjective()
    score = obj.compute(_metrics())
    assert score > 0.8


def test_low_yield_reduces_score():
    obj = CultureObjective()
    high = obj.compute(_metrics())
    low = obj.compute(_metrics(vcd_final=10e6))
    assert low < high


def test_constraint_penalty():
    obj = CultureObjective()
    normal = obj.compute(_metrics())
    violated = obj.compute(_metrics(max_lactate_mm=60.0))
    assert violated < normal


def test_aggregate_size_optimal_range():
    obj = CultureObjective()
    optimal = obj.compute(_metrics(mean_aggregate_diameter_um=250.0))
    too_large = obj.compute(_metrics(mean_aggregate_diameter_um=500.0))
    too_small = obj.compute(_metrics(mean_aggregate_diameter_um=100.0))
    assert optimal > too_large
    assert optimal > too_small
