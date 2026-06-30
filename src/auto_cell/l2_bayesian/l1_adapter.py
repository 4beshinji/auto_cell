"""Adapter between L2 Bayesian-optimization parameters and L1 recipe/plant.

This module is intentionally thin: it maps the ``CultureSearchSpace`` used by
``BayesianOptimizer`` onto the ``Recipe.setpoints`` / ``Recipe.variables`` used
by ``RecipeEngine``, and onto the keyword arguments of ``sim.plant_model.seed_state``.
After a run it converts a sequence of ``CycleResult`` objects plus the final
``CellCultureEnv`` into the ``RunMetrics`` expected by the optimizer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from auto_cell.l1.recipe_loader import load_recipe
from auto_cell.l1.types import Recipe, ScalarValue
from auto_cell.l2_bayesian.objective import RunMetrics
from auto_cell.l2_bayesian.space import PerfusionRampProfile
from auto_cell.plugins.cell_culture.aggregate_imaging import AggregateMetrics
from auto_cell.plugins.cell_culture.environment import CellCultureEnv


class L1Adapter:
    """Translate L2 BO parameters to L1 execution context and back to metrics."""

    # Simplified linear-ramp end time [h] per profile. Phase 2 uses discrete
    # profiles; continuous parameterization is left to Phase 3.
    PROFILE_RAMP_END_H: dict[str, float] = {
        PerfusionRampProfile.MANSTEIN_LINEAR.value: 120.0,
        PerfusionRampProfile.CONSERVATIVE.value: 168.0,
        PerfusionRampProfile.AGGRESSIVE.value: 72.0,
    }

    DEFAULT_PLURIPOTENCY_PCT = 0.9
    DEFAULT_MEDIA_COST_PER_VVD = 100.0

    def __init__(
        self,
        *,
        pluripotency_pct: float = DEFAULT_PLURIPOTENCY_PCT,
        media_cost_per_vvd: float = DEFAULT_MEDIA_COST_PER_VVD,
    ) -> None:
        self.pluripotency_pct = pluripotency_pct
        self.media_cost_per_vvd = media_cost_per_vvd

    def apply_bo_params_to_recipe(
        self,
        params: dict[str, Any],
        base_recipe_path: str | Path,
    ) -> Recipe:
        """Return a recipe whose setpoints/variables reflect *params*."""
        recipe = load_recipe(base_recipe_path)

        # Map BO parameter names to recipe keys.
        variable_overrides: dict[str, ScalarValue] = {}
        setpoint_overrides: dict[str, ScalarValue] = {}

        if "seeding_density" in params:
            variable_overrides["seed_density"] = ScalarValue(
                value=params["seeding_density"], unit="cells/mL"
            )
        if "max_perfusion_rate_vvd" in params:
            variable_overrides["max_perfusion"] = ScalarValue(
                value=params["max_perfusion_rate_vvd"], unit="vvd"
            )
        if "perfusion_ramp_profile" in params:
            profile = params["perfusion_ramp_profile"]
            variable_overrides["perfusion_ramp_end_h"] = ScalarValue(
                value=self.PROFILE_RAMP_END_H.get(profile, 120.0), unit="h"
            )
        if "y_27632_conc_um" in params:
            variable_overrides["y_27632_conc_um"] = ScalarValue(
                value=params["y_27632_conc_um"], unit="uM"
            )

        if "agitation_base_rpm" in params:
            setpoint_overrides["agitation"] = ScalarValue(
                value=params["agitation_base_rpm"], unit="rpm"
            )
        if "do_transition_end_pct" in params:
            setpoint_overrides["do_late"] = ScalarValue(
                value=params["do_transition_end_pct"], unit="%"
            )

        new_variables = {**recipe.variables, **variable_overrides}
        new_setpoints = {**recipe.setpoints, **setpoint_overrides}
        return recipe.model_copy(
            update={"variables": new_variables, "setpoints": new_setpoints}
        )

    def get_plant_seed_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Return kwargs for ``sim.plant_model.seed_state`` derived from *params*."""
        seed_kwargs: dict[str, Any] = {}
        if "seeding_density" in params:
            seed_kwargs["seeding_density"] = params["seeding_density"]
        if "initial_glucose_mm" in params:
            seed_kwargs["initial_glucose"] = params["initial_glucose_mm"]
        return seed_kwargs

    def apply_aggregate_metrics_to_env(
        self,
        aggregate_metrics: AggregateMetrics,
        final_env: CellCultureEnv,
    ) -> None:
        """Override aggregate fields in ``final_env`` with image-derived metrics."""
        final_env.aggregate_diameter_um = aggregate_metrics.mean_diameter_um
        final_env.large_aggregate_ratio = aggregate_metrics.large_aggregate_ratio
        final_env.circularity = aggregate_metrics.mean_circularity
        final_env.aspect_ratio = aggregate_metrics.mean_aspect_ratio

    def collect_run_metrics(
        self,
        cycle_results: list[Any],
        final_env: CellCultureEnv,
        perfusion_demand: float | None = None,
        aggregate_metrics: AggregateMetrics | None = None,
    ) -> RunMetrics:
        """Aggregate L1 run history into the scalar metrics BO consumes.

        Args:
            cycle_results: Audit log of ``CycleResult`` produced by ``L1CycleExecutor``.
            final_env: Environment state at the end of the run.
            perfusion_demand: Total perfusion volume in vessel-volumes. If omitted,
                it is approximated from ``final_env.perfusion_rate_vvd`` and culture
                age, which is a rough lower bound.
            aggregate_metrics: Optional image-derived aggregate metrics. When provided,
                the corresponding fields in ``final_env`` are overridden before
                constructing ``RunMetrics``.
        """
        if aggregate_metrics is not None:
            self.apply_aggregate_metrics_to_env(aggregate_metrics, final_env)

        max_lactate = 0.0
        max_osmolality = 0.0

        for result in cycle_results:
            env = getattr(result, "sensor_snapshot", None)
            if env is None:
                continue
            max_lactate = max(max_lactate, getattr(env, "lactate_mM", 0.0))
            max_osmolality = max(
                max_osmolality, getattr(env, "osmolality_mOsm_kg", 0.0)
            )

        if perfusion_demand is None:
            # Rough approximation: average perfusion rate × culture age in days.
            # This intentionally ignores bolus feeds and ramp shape.
            age_d = max(final_env.culture_age_d, 0.0)
            perfusion_demand = final_env.perfusion_rate_vvd * age_d

        total_run_cost = perfusion_demand * self.media_cost_per_vvd

        return RunMetrics(
            vcd_final=final_env.vcd,
            viability_final=final_env.viability_pct / 100.0,
            pluripotency_pct=self.pluripotency_pct,
            mean_aggregate_diameter_um=final_env.aggregate_diameter_um or 0.0,
            large_aggregate_ratio=final_env.large_aggregate_ratio,
            total_run_cost=total_run_cost,
            max_lactate_mm=max_lactate,
            max_osmolality_mosm=max_osmolality,
        )
