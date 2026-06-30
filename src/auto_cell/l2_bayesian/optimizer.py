"""Thin Ax wrapper for run-to-run Bayesian optimization.

Note: `AxClient` is used here because it is the API referenced in the Phase 1
plan (`M06_bo_llm_imaging_implementation_plan.md`). Ax 1.3.x deprecates it in
favor of `ax.api.Client`; a future Phase 2 refactor should migrate to the new
API once it stabilizes.
"""

from __future__ import annotations

import random
import warnings
from typing import Any

import numpy as np
import torch
from ax.service.ax_client import AxClient
from ax.service.utils.instantiation import ObjectiveProperties

from auto_cell.l2_bayesian.constants import (
    OBJECTIVE_METRIC,
    SAFE_BO_OUTCOME_CONSTRAINTS,
)
from auto_cell.l2_bayesian.objective import CultureObjective, RunMetrics
from auto_cell.l2_bayesian.space import CultureSearchSpace, PerfusionRampProfile


class BayesianOptimizer:
    """Run-level Bayesian optimization engine wrapping AxClient.

    Reproducibility is guaranteed for the Sobol initialization trials by fixing
    Python, NumPy, and Torch random seeds. BoTorch model trials may diverge over
    time, so reproducibility tests should focus on the first trial(s).
    """

    def __init__(
        self,
        seed: int = 42,
        objective: CultureObjective | None = None,
        minimize: bool = False,
    ):
        self.seed = seed
        self.objective = objective or CultureObjective()
        self.minimize = minimize
        self._set_seeds()

        # Suppress AxClient deprecation warning for Phase 1 skeleton clarity.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            self.ax = AxClient(random_seed=seed)

        self.ax.create_experiment(
            name="ipsc_perfusion_phase1",
            parameters=CultureSearchSpace(
                seeding_density=0.5e6,
                initial_glucose_mm=17.5,
                perfusion_ramp_profile=PerfusionRampProfile.MANSTEIN_LINEAR,
                max_perfusion_rate_vvd=3.5,
                agitation_base_rpm=80,
                do_transition_end_pct=10.0,
                y_27632_conc_um=5.0,
            ).to_ax_parameters(),
            objectives={
                OBJECTIVE_METRIC: ObjectiveProperties(minimize=minimize)
            },
            outcome_constraints=SAFE_BO_OUTCOME_CONSTRAINTS,
        )

    def _set_seeds(self) -> None:
        random.seed(self.seed)
        np.random.seed(self.seed)
        torch.manual_seed(self.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.seed)

    def suggest(self) -> tuple[int, dict[str, Any]]:
        """Suggest the next trial. Returns (trial_index, parameters)."""
        params, trial_index = self.ax.get_next_trial()
        return trial_index, params

    def complete_trial(self, trial_index: int, metrics: RunMetrics) -> None:
        """Complete a trial with observed run metrics."""
        objective_value = self.objective.compute(metrics)
        self.ax.complete_trial(
            trial_index=trial_index,
            raw_data={
                OBJECTIVE_METRIC: objective_value,
                "max_lactate_mm": metrics.max_lactate_mm,
                "max_osmolality_mosm": metrics.max_osmolality_mosm,
                "large_aggregate_ratio": metrics.large_aggregate_ratio,
                "viability_final": metrics.viability_final,
            },
        )

    def get_best_parameters(self) -> dict[str, Any] | None:
        """Return the best parameter configuration seen so far, or None."""
        best = self.ax.get_best_parameters()
        if best is None:
            return None
        params, _ = best
        return params
