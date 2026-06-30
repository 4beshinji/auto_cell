"""Integration tests for L2 Bayesian optimization wired to the L1 cycle."""

from __future__ import annotations

from pathlib import Path

import pytest

from auto_cell.l1.recipe_engine import RecipeEngine
from auto_cell.l1.types import CycleResult
from auto_cell.l2_bayesian import (
    L1Adapter,
    PerfusionRampProfile,
    RunOrchestrator,
)
from auto_cell.l2_bayesian.objective import RunMetrics
from auto_cell.plugins.cell_culture.environment import CellCultureEnv


RECIPE_PATH = Path(__file__).parent.parent.parent / "config" / "recipes" / "manstein_phase1.yaml"
RULES_PATH = Path(__file__).parent.parent.parent / "config" / "recipes" / "manstein_rules.yaml"


@pytest.fixture
def adapter() -> L1Adapter:
    return L1Adapter(media_cost_per_vvd=100.0)


def test_adapter_maps_bo_params_to_recipe(adapter: L1Adapter) -> None:
    params = {
        "seeding_density": 1.0e6,
        "initial_glucose_mm": 20.0,
        "perfusion_ramp_profile": PerfusionRampProfile.CONSERVATIVE.value,
        "max_perfusion_rate_vvd": 4.0,
        "agitation_base_rpm": 90,
        "do_transition_end_pct": 12.0,
        "y_27632_conc_um": 7.5,
    }

    recipe = adapter.apply_bo_params_to_recipe(params, RECIPE_PATH)

    assert recipe.variables["seed_density"].value == pytest.approx(1.0e6)
    assert recipe.variables["max_perfusion"].value == pytest.approx(4.0)
    assert recipe.variables["y_27632_conc_um"].value == pytest.approx(7.5)
    assert recipe.variables["perfusion_ramp_end_h"].value == pytest.approx(168.0)
    assert recipe.setpoints["agitation"].value == 90
    assert recipe.setpoints["do_late"].value == pytest.approx(12.0)


def test_adapter_get_plant_seed_params() -> None:
    adapter = L1Adapter()
    params = {"seeding_density": 0.8e6, "initial_glucose_mm": 18.0}
    seed_kwargs = adapter.get_plant_seed_params(params)
    assert seed_kwargs == {"seeding_density": 0.8e6, "initial_glucose": 18.0}


def test_adapter_collects_metrics_from_cycle_results(adapter: L1Adapter) -> None:
    env = CellCultureEnv(
        vcd=30e6,
        viability_pct=95.0,
        glucose_mM=5.0,
        lactate_mM=40.0,
        glutamine_mM=1.0,
        ph=7.1,
        do_pct=20.0,
        temp_c=37.0,
        osmolality_mOsm_kg=380.0,
        agitation_rpm=80.0,
        perfusion_rate_vvd=3.0,
        culture_age_d=7.0,
        aggregate_diameter_um=250.0,
        large_aggregate_ratio=0.05,
    )
    result = CycleResult(
        cycle=1,
        elapsed_hours=1.0,
        state_id="perfusion_ramp",
        sensor_snapshot=env,
        events=[],
        candidates=[],
        executed=[],
        rejected=[],
        approval_requested=[],
    )

    metrics = adapter.collect_run_metrics([result], env)

    assert isinstance(metrics, RunMetrics)
    assert metrics.vcd_final == pytest.approx(30e6)
    assert metrics.viability_final == pytest.approx(0.95)
    assert metrics.max_lactate_mm == pytest.approx(40.0)
    assert metrics.max_osmolality_mosm == pytest.approx(380.0)
    assert metrics.total_run_cost == pytest.approx(3.0 * 7.0 * 100.0)


def test_run_orchestrator_executes_one_trial() -> None:
    orchestrator = RunOrchestrator(
        base_recipe_path=RECIPE_PATH,
        rules_path=RULES_PATH,
        seed=12345,
        media_cost_per_vvd=100.0,
    )
    config = orchestrator.suggest_and_prepare_run()

    assert config.trial_index == 0
    assert "seeding_density" in config.params
    assert isinstance(config.recipe, RecipeEngine)

    result = orchestrator.execute_run(config, max_hours=168.0, dt=300.0)

    assert result.completed
    assert result.final_env is not None
    assert result.final_env.vcd > 0.0
    assert len(result.cycle_results) > 0

    orchestrator.complete_run(result)
    best = orchestrator.optimizer.get_best_parameters()
    assert best is not None


def test_run_orchestrator_runs_multiple_trials() -> None:
    orchestrator = RunOrchestrator(
        base_recipe_path=RECIPE_PATH,
        rules_path=RULES_PATH,
        seed=42,
        media_cost_per_vvd=100.0,
    )
    results = orchestrator.run_n(2, max_hours=168.0, dt=300.0)

    assert len(results) == 2
    assert all(r.completed for r in results)
    assert all(r.final_env is not None for r in results)

    best = orchestrator.optimizer.get_best_parameters()
    assert best is not None


def test_bo_suggestion_is_deterministic_with_same_seed() -> None:
    orch1 = RunOrchestrator(
        base_recipe_path=RECIPE_PATH,
        rules_path=RULES_PATH,
        seed=999,
        media_cost_per_vvd=100.0,
    )
    orch2 = RunOrchestrator(
        base_recipe_path=RECIPE_PATH,
        rules_path=RULES_PATH,
        seed=999,
        media_cost_per_vvd=100.0,
    )

    cfg1 = orch1.suggest_and_prepare_run()
    cfg2 = orch2.suggest_and_prepare_run()

    assert cfg1.trial_index == cfg2.trial_index
    assert cfg1.params == cfg2.params
