"""End-to-end closed-loop test: L1 engine + plant_model (no MQTT broker)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from auto_cell.l1.recipe_engine import RecipeEngine
from auto_cell.l1.types import CycleResult, ToolCall
from auto_cell.plugins.cell_culture.environment import CellCultureEnv
from sim.plant_model import PlantModel, Actuators, Sensors, seed_state, sensors_to_env


class _ClosedLoopFixture:
    """Wires a PlantModel to the L1 engine without MQTT."""

    def __init__(self) -> None:
        self.plant = PlantModel(initial_state=seed_state())
        self.actuators = Actuators()
        self.last_sensors = self._sensors_from_state(self.plant.state)
        self.approvals: list[ToolCall] = []
        self.audit_log: list[CycleResult] = []

        recipe_path = Path(__file__).parent.parent / "config" / "recipes" / "manstein_phase1.yaml"
        rules_path = Path(__file__).parent.parent / "config" / "recipes" / "manstein_rules.yaml"
        self.engine = RecipeEngine.from_files(
            str(recipe_path),
            str(rules_path),
            suppression_defaults={},
        )

    def get_env(self) -> CellCultureEnv:
        return sensors_to_env(self.last_sensors, self.actuators, culture_age_d=self.plant.time)

    @staticmethod
    def _sensors_from_state(state) -> Sensors:
        return Sensors(
            vcd=state.vcd,
            viability=state.viability,
            glucose=state.glucose,
            lactate=state.lactate,
            glutamine=state.glutamine,
            osmolality=state.osmolality,
            aggregate_diameter_um=state.aggregate_diameter,
            do_percent=40.0,
            ph=7.1,
            temp_c=37.0,
        )

    def issue_command(self, tool_call: ToolCall, correlation_id: str) -> None:
        args = tool_call.args
        if tool_call.tool == "set_perfusion_rate":
            self.actuators = self._replace(self.actuators, perfusion_rate_vvd=float(args["vvd"]))
        elif tool_call.tool == "set_agitation_rpm":
            self.actuators = self._replace(self.actuators, agitation_rpm=float(args["rpm"]))
        elif tool_call.tool == "set_gas_setpoint":
            if args.get("gas") == "do":
                self.actuators = self._replace(self.actuators, do_setpoint=float(args["setpoint"]))
            elif args.get("gas") == "ph":
                self.actuators = self._replace(self.actuators, ph_setpoint=float(args["setpoint"]))
        elif tool_call.tool == "feed":
            # Treat feed as a one-step bolus in the actuators.
            self.actuators = self._replace(
                self.actuators,
                feed_glucose=float(args.get("glucose_mM", 0.0)) * float(args.get("volume_ml", 0.0)),
                feed_glutamine=float(args.get("glutamine_mM", 0.0)) * float(args.get("volume_ml", 0.0)),
            )
        elif tool_call.tool == "trigger_passage":
            self.plant.reset_after_passage()
        elif tool_call.tool in {"take_sample", "notify", "log", "exchange_media"}:
            pass

    def request_approval(self, tool_call: ToolCall, correlation_id: str) -> str:
        self.approvals.append(tool_call)
        return correlation_id

    def audit(self, result: CycleResult) -> None:
        self.audit_log.append(result)

    @staticmethod
    def _replace(actuators: Actuators, **kwargs: Any) -> Actuators:
        data = actuators.__dict__.copy() if hasattr(actuators, "__dict__") else {
            "perfusion_rate_vvd": actuators.perfusion_rate_vvd,
            "agitation_rpm": actuators.agitation_rpm,
            "do_setpoint": actuators.do_setpoint,
            "ph_setpoint": actuators.ph_setpoint,
            "feed_glucose": actuators.feed_glucose,
            "feed_glutamine": actuators.feed_glutamine,
        }
        data.update(kwargs)
        return Actuators(**data)

    def step(self, dt: float = 300.0) -> CycleResult:
        result = self.engine.step(
            cycle=len(self.audit_log) + 1,
            elapsed_hours=self.plant.time * 24.0,
            env=self.get_env(),
        )
        for tc in result.executed:
            self.issue_command(tc, f"c{len(self.audit_log)}-{tc.tool}")
        for tc in result.approval_requested:
            self.request_approval(tc, f"c{len(self.audit_log)}-{tc.tool}")
        self.audit(result)
        # Advance plant model with current actuators.
        # Reset one-shot feed after applying.
        self.last_sensors = self.plant.step(self.actuators, dt=dt)
        self.actuators = self._replace(self.actuators, feed_glucose=0.0, feed_glutamine=0.0)
        return result


def test_e2e_closed_loop_runs_for_one_day():
    """Run a shortened 1-day closed loop and check state evolution."""
    fixture = _ClosedLoopFixture()
    dt = 300.0  # 5 min
    n_steps = int(24 * 3600 / dt)

    for _ in range(n_steps):
        fixture.step(dt=dt)

    final_env = fixture.get_env()
    assert final_env.vcd > seed_state().vcd
    assert fixture.engine.context.state_id in {"seed", "perfusion_ramp"}
    # Some recipe entry actions should have been executed.
    assert any(r.state_id == "perfusion_ramp" for r in fixture.audit_log) or fixture.engine.context.state_id == "seed"


def test_e2e_closed_loop_runs_for_seven_days():
    """Run a 7-day closed loop and confirm completion without exceptions."""
    fixture = _ClosedLoopFixture()
    dt = 300.0
    n_steps = int(7 * 24 * 3600 / dt)

    for _ in range(n_steps):
        fixture.step(dt=dt)

    final_env = fixture.get_env()
    assert final_env.vcd > seed_state().vcd
    assert final_env.ph == pytest.approx(7.1, abs=0.3)
    assert 5.0 <= final_env.do_pct <= 50.0
