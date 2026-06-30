"""Tests for BayesianOptimizer reproducibility and basic workflow."""

from __future__ import annotations

from auto_cell.l2_bayesian.objective import RunMetrics
from auto_cell.l2_bayesian.optimizer import BayesianOptimizer


def test_suggest_is_reproducible_with_same_seed():
    """Sobol initialization should be deterministic with fixed seeds."""
    opt1 = BayesianOptimizer(seed=12345)
    opt2 = BayesianOptimizer(seed=12345)

    idx1, params1 = opt1.suggest()
    idx2, params2 = opt2.suggest()

    assert params1 == params2
    assert idx1 == idx2


def test_complete_trial_updates_best():
    opt = BayesianOptimizer(seed=1)
    idx, params = opt.suggest()

    metrics = RunMetrics(
        vcd_final=35e6,
        viability_final=0.95,
        pluripotency_pct=0.92,
        mean_aggregate_diameter_um=250.0,
        large_aggregate_ratio=0.05,
        total_run_cost=800.0,
        max_lactate_mm=30.0,
        max_osmolality_mosm=420.0,
    )
    opt.complete_trial(idx, metrics)
    best = opt.get_best_parameters()
    assert best is not None
    assert best == params


def test_different_seed_gives_different_first_trial():
    opt1 = BayesianOptimizer(seed=1)
    opt2 = BayesianOptimizer(seed=2)
    _, params1 = opt1.suggest()
    _, params2 = opt2.suggest()
    assert params1 != params2
