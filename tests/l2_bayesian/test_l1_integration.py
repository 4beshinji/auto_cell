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
from auto_cell.plugins.cell_culture.aggregate_imaging import AggregateMetrics
from auto_cell.plugins.cell_culture.aggregate_imaging_service import (
    AggregateImagingService,
)
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


def test_aggregate_metrics_override_run_metrics(adapter: L1Adapter) -> None:
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
    aggregate_metrics = AggregateMetrics(
        mean_diameter_um=300.0,
        large_aggregate_ratio=0.25,
        mean_circularity=0.85,
        mean_aspect_ratio=1.2,
        n_objects=10,
        pixel_size_um=1.0,
    )

    metrics = adapter.collect_run_metrics(
        [], env, aggregate_metrics=aggregate_metrics
    )

    assert metrics.mean_aggregate_diameter_um == pytest.approx(300.0)
    assert metrics.large_aggregate_ratio == pytest.approx(0.25)
    assert env.aggregate_diameter_um == pytest.approx(300.0)


def test_aggregate_imaging_service_updates_env_and_fires_events() -> None:
    import numpy as np
    from skimage.draw import disk
    from skimage.measure import label

    img = np.zeros((256, 256), dtype=np.uint8)
    rr, cc = disk((128, 128), 60, shape=img.shape)
    img[rr, cc] = 255
    masks = label(img > 0)

    service = AggregateImagingService(pixel_size_um=3.0, large_threshold_um=400.0)
    env = CellCultureEnv(
        vcd=10e6,
        viability_pct=95.0,
        glucose_mM=5.0,
        lactate_mM=5.0,
        glutamine_mM=2.0,
        ph=7.1,
        do_pct=40.0,
        temp_c=37.0,
        osmolality_mOsm_kg=300.0,
        agitation_rpm=80.0,
        perfusion_rate_vvd=3.0,
        culture_age_d=3.0,
    )

    metrics, _, events = service.process(
        masks, env, run_id="run_1", sample_id="sample_C", is_mask=True
    )

    assert metrics.n_objects == 1
    assert env.aggregate_diameter_um == metrics.mean_diameter_um
    event_ids = {e.event_id for e in events}
    assert "aggregate_out_of_range" in event_ids


def test_run_orchestrator_uses_aggregate_image(tmp_path: Path) -> None:
    import numpy as np
    from skimage.draw import disk
    from skimage.measure import label

    img = np.zeros((256, 256), dtype=np.uint8)
    rr, cc = disk((128, 128), 50, shape=img.shape)
    img[rr, cc] = 255
    masks = label(img > 0)

    orchestrator = RunOrchestrator(
        base_recipe_path=RECIPE_PATH,
        rules_path=RULES_PATH,
        seed=111,
        media_cost_per_vvd=100.0,
    )
    config = orchestrator.suggest_and_prepare_run()
    result = orchestrator.execute_run(
        config,
        max_hours=24.0,
        dt=300.0,
        aggregate_image=masks,
        aggregate_is_mask=True,
        artifact_dir=tmp_path,
    )

    assert result.completed
    assert result.final_env is not None
    assert result.aggregate_metrics is not None
    assert result.final_env.aggregate_diameter_um == pytest.approx(
        result.aggregate_metrics.mean_diameter_um
    )

    orchestrator.complete_run(result)
    best = orchestrator.optimizer.get_best_parameters()
    assert best is not None
