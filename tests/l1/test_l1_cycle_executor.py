"""Tests for the synchronous L1 cycle executor."""

from __future__ import annotations

from auto_cell.l1.cycle_executor import L1CycleExecutor
from auto_cell.l1.recipe_engine import RecipeEngine
from auto_cell.plugins.cell_culture.environment import CellCultureEnv


def test_cycle_runs_without_approval():
    recipe = RecipeEngine.from_files(
        "config/recipes/manstein_phase1.yaml",
        "config/recipes/manstein_rules.yaml",
        suppression_defaults={},
    )
    commands = []
    approvals = []

    def issue(tc, correlation_id):
        commands.append(tc.tool)

    def request(tc, correlation_id):
        approvals.append(tc.tool)

    env = CellCultureEnv(
        vcd=0.6e6,
        viability_pct=97.0,
        glucose_mM=5.0,
        lactate_mM=5.0,
        glutamine_mM=2.0,
        ph=7.1,
        do_pct=40.0,
        temp_c=37.0,
        osmolality_mOsm_kg=300.0,
        agitation_rpm=80.0,
        perfusion_rate_vvd=0.0,
        culture_age_d=0.025,  # ~0.6 h
    )

    exec_ = L1CycleExecutor(
        recipe_engine=recipe,
        get_env=lambda: env,
        issue_command=issue,
        request_approval=request,
        audit=lambda x: None,
    )
    result = exec_.run_once()
    assert result.state_id == "perfusion_ramp"
    assert "set_gas_setpoint" in commands
