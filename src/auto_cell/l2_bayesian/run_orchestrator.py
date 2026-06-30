"""Run-to-run orchestrator wiring L2 Bayesian optimization to the L1 cycle.

The orchestrator is simulator-first: it drives ``sim.plant_model.PlantModel`` with
``auto_cell.l1.L1CycleExecutor``. Each completed run feeds scalar metrics back to
``BayesianOptimizer`` so the next run's setpoints are optimized.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from auto_cell.l1.cycle_executor import L1CycleExecutor
from auto_cell.l1.recipe_engine import RecipeEngine
from auto_cell.l1.types import CycleResult, ToolCall
from auto_cell.l2_bayesian.l1_adapter import L1Adapter
from auto_cell.l2_bayesian.optimizer import BayesianOptimizer
from auto_cell.plugins.cell_culture.aggregate_imaging import AggregateMetrics
from auto_cell.plugins.cell_culture.aggregate_imaging_service import (
    AggregateImagingService,
)
from auto_cell.plugins.cell_culture.environment import CellCultureEnv

logger = logging.getLogger(__name__)

# Terminal L1 states that end a run for optimization purposes.
_TERMINAL_STATES = {"passage_ready", "approved_passage", "hold", "reseed"}


@dataclass
class RunConfig:
    """Inputs for one BO trial / one simulated run."""

    trial_index: int
    params: dict[str, Any]
    recipe: RecipeEngine
    seed_kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunResult:
    """Outputs from one simulated run."""

    trial_index: int
    params: dict[str, Any]
    cycle_results: list[CycleResult] = field(default_factory=list)
    final_env: CellCultureEnv | None = None
    aggregate_metrics: AggregateMetrics | None = None
    completed: bool = False


class RunOrchestrator:
    """Coordinate suggest → execute → complete loops between L2 and L1."""

    def __init__(
        self,
        base_recipe_path: str | Path,
        rules_path: str | Path,
        *,
        seed: int = 42,
        state_dir: str | Path | None = None,
        adapter: L1Adapter | None = None,
        optimizer: BayesianOptimizer | None = None,
        suppression_defaults: dict[str, float] | None = None,
        media_cost_per_vvd: float = L1Adapter.DEFAULT_MEDIA_COST_PER_VVD,
    ) -> None:
        self.base_recipe_path = Path(base_recipe_path)
        self.rules_path = Path(rules_path)
        self.adapter = adapter or L1Adapter(media_cost_per_vvd=media_cost_per_vvd)
        self.optimizer = optimizer or BayesianOptimizer(seed=seed)
        self.seed = seed
        self.state_dir = Path(state_dir) if state_dir else Path("data/bo_state")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.suppression_defaults = suppression_defaults or {}

    @staticmethod
    def _sensors_from_state(state: Any, actuators: Any) -> Any:
        """Build Sensors from PlantState + Actuators (mirrors sim.plant_model)."""
        from sim.plant_model import Sensors

        return Sensors(
            vcd=state.vcd,
            viability=state.viability,
            glucose=state.glucose,
            lactate=state.lactate,
            glutamine=state.glutamine,
            osmolality=state.osmolality,
            aggregate_diameter_um=state.aggregate_diameter,
            do_percent=actuators.do_setpoint,
            ph=actuators.ph_setpoint,
            temp_c=37.0,
        )

    def suggest_and_prepare_run(self) -> RunConfig:
        """Ask L2 for the next trial and build an L1 recipe from it."""
        trial_index, params = self.optimizer.suggest()
        recipe = self.adapter.apply_bo_params_to_recipe(
            params, self.base_recipe_path
        )
        seed_kwargs = self.adapter.get_plant_seed_params(params)
        rules = RecipeEngine.from_files(
            str(self.base_recipe_path),
            str(self.rules_path),
            suppression_defaults=self.suppression_defaults,
        ).rules
        engine = RecipeEngine(
            recipe=recipe,
            rules=rules,
            suppression_defaults=self.suppression_defaults,
        )
        return RunConfig(
            trial_index=trial_index,
            params=params,
            recipe=engine,
            seed_kwargs=seed_kwargs,
        )

    def execute_run(
        self,
        config: RunConfig,
        *,
        max_hours: float = 168.0,
        dt: float = 300.0,
        auto_approve: bool = True,
        aggregate_image: str | Path | np.ndarray | None = None,
        aggregate_is_mask: bool = False,
        artifact_dir: str | Path | None = None,
    ) -> RunResult:
        """Execute one run against the plant_model until completion or timeout.

        Args:
            config: Run configuration from ``suggest_and_prepare_run``.
            max_hours: Hard stop for the simulated run.
            dt: Plant integration step in seconds.
            auto_approve: If True, approval requests are automatically approved.
                Real HITL runs should set this to False and wire an approval service.
            aggregate_image: Optional at-line aggregate image (or mask) to analyze
                at the end of the run and override simulator-derived aggregate metrics.
            aggregate_is_mask: If True, ``aggregate_image`` is treated as a labeled mask.
            artifact_dir: Directory to save aggregate image artifacts.
        """
        # Deferred import to avoid coupling L2 to sim at module load time.
        from sim.plant_model import PlantModel, Actuators, seed_state, sensors_to_env

        plant = PlantModel(initial_state=seed_state(**config.seed_kwargs))
        actuators = Actuators()
        last_sensors = self._sensors_from_state(plant.state, actuators)
        audit_log: list[CycleResult] = []
        pending_approvals: dict[str, str] = {}

        def get_env() -> CellCultureEnv:
            return sensors_to_env(
                last_sensors, actuators, culture_age_d=plant.time
            )

        def issue_command(tool_call: ToolCall, correlation_id: str) -> None:
            nonlocal actuators
            args = tool_call.args
            if tool_call.tool == "set_perfusion_rate":
                actuators = _actuators_replace(
                    actuators, perfusion_rate_vvd=float(args["vvd"])
                )
            elif tool_call.tool == "set_agitation_rpm":
                actuators = _actuators_replace(
                    actuators, agitation_rpm=float(args["rpm"])
                )
            elif tool_call.tool == "set_gas_setpoint":
                if args.get("gas") == "do":
                    actuators = _actuators_replace(
                        actuators, do_setpoint=float(args["setpoint"])
                    )
                elif args.get("gas") == "ph":
                    actuators = _actuators_replace(
                        actuators, ph_setpoint=float(args["setpoint"])
                    )
            elif tool_call.tool == "feed":
                actuators = _actuators_replace(
                    actuators,
                    feed_glucose=float(args.get("glucose_mM", 0.0))
                    * float(args.get("volume_ml", 0.0)),
                    feed_glutamine=float(args.get("glutamine_mM", 0.0))
                    * float(args.get("volume_ml", 0.0)),
                )
            elif tool_call.tool == "trigger_passage":
                plant.reset_after_passage()

        def request_approval(tool_call: ToolCall, correlation_id: str) -> str:
            if auto_approve:
                pending_approvals[correlation_id] = "approved"
                # Re-run approval state in the engine on next cycle.
                config.recipe.approvals.update(pending_approvals)
                return correlation_id
            pending_approvals[correlation_id] = "pending"
            return correlation_id

        def audit(result: CycleResult) -> None:
            audit_log.append(result)

        executor = L1CycleExecutor(
            recipe_engine=config.recipe,
            get_env=get_env,
            issue_command=issue_command,
            request_approval=request_approval,
            audit=audit,
            cycle_interval_seconds=dt,
        )

        max_cycles = int(max_hours * 3600 / dt)
        completed = False
        for _ in range(max_cycles):
            result = executor.run_once()
            last_sensors = plant.step(actuators, dt=dt)
            # Reset one-shot feed actuators after they have been applied.
            actuators = _actuators_replace(
                actuators, feed_glucose=0.0, feed_glutamine=0.0
            )

            if result.state_id in _TERMINAL_STATES:
                completed = True
                break
        else:
            # Loop finished without reaching a terminal state (max-hours timeout).
            completed = True

        final_env = get_env()
        aggregate_metrics: AggregateMetrics | None = None
        if aggregate_image is not None:
            imaging = AggregateImagingService(
                pixel_size_um=1.0, artifact_dir=artifact_dir
            )
            sample_id = f"trial_{config.trial_index}"
            run_id = f"run_trial_{config.trial_index}"
            aggregate_metrics, _, _ = imaging.process(
                aggregate_image,
                final_env,
                run_id=run_id,
                sample_id=sample_id,
                is_mask=aggregate_is_mask,
            )

        return RunResult(
            trial_index=config.trial_index,
            params=config.params,
            cycle_results=audit_log,
            final_env=final_env,
            aggregate_metrics=aggregate_metrics,
            completed=completed,
        )

    def complete_run(self, result: RunResult) -> None:
        """Feed *result* back into the Bayesian optimizer."""
        if result.final_env is None:
            raise ValueError("cannot complete run without final_env")
        metrics = self.adapter.collect_run_metrics(
            result.cycle_results,
            result.final_env,
            aggregate_metrics=result.aggregate_metrics,
        )
        self.optimizer.complete_trial(result.trial_index, metrics)
        logger.info(
            "completed trial %d objective=%.4f vcd=%.2e",
            result.trial_index,
            self.optimizer.objective.compute(metrics),
            metrics.vcd_final,
        )

    def run_n(
        self,
        n: int,
        *,
        max_hours: float = 168.0,
        dt: float = 300.0,
        aggregate_images: list[str | Path | np.ndarray] | None = None,
        aggregate_is_mask: bool = False,
        artifact_dir: str | Path | None = None,
    ) -> list[RunResult]:
        """Run the full suggest → execute → complete loop *n* times."""
        aggregate_images = aggregate_images or []
        results: list[RunResult] = []
        for i in range(n):
            config = self.suggest_and_prepare_run()
            aggregate_image = aggregate_images[i] if i < len(aggregate_images) else None
            result = self.execute_run(
                config,
                max_hours=max_hours,
                dt=dt,
                aggregate_image=aggregate_image,
                aggregate_is_mask=aggregate_is_mask,
                artifact_dir=artifact_dir,
            )
            self.complete_run(result)
            results.append(result)
        return results

    def save_state(self, name: str = "optimizer_state") -> Path:
        """Persist AxClient state to JSON."""
        path = self.state_dir / f"{name}.json"
        self.optimizer.ax.save_to_json_file(str(path))
        return path

    @classmethod
    def load_state(
        cls,
        path: str | Path,
        base_recipe_path: str | Path,
        rules_path: str | Path,
    ) -> "RunOrchestrator":
        """Restore an orchestrator from a saved AxClient JSON file."""
        from ax.service.ax_client import AxClient

        orchestrator = cls(
            base_recipe_path=base_recipe_path,
            rules_path=rules_path,
        )
        orchestrator.optimizer.ax = AxClient.load_from_json_file(str(path))
        return orchestrator


def _actuators_replace(actuators: Any, **kwargs: Any) -> Any:
    """Backwards-compatible helper to update frozen Actuators dataclass."""
    data = actuators.__dict__.copy()
    data.update(kwargs)
    return actuators.__class__(**data)
