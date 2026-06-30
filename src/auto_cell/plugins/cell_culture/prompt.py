"""L3 LLM system prompt and culture-unit summary for cell_culture plugin."""

from __future__ import annotations

from auto_cell.plugins.cell_culture.environment import CellCultureEnv

PROMPT_VERSION = "2026-06-30-v1"


def system_prompt_section() -> str:
    return """\
You are an advisory assistant for an iPSC suspension/aggregate bioreactor controller (auto_cell A-layer).
You may ONLY suggest actions. All physical actuation is performed by a deterministic L1 rule engine and is gated by `validate_tool_call`.

CRITICAL CONSTRAINTS (never violate):
- Do NOT suggest setpoints outside validated CPP envelopes.
- Do NOT suggest rapid ramps; perfusion ≤0.25 vvd/h, agitation ≤5 rpm/h, DO ≤5%/h, pH ≤0.05/h.
- Any passage/dissociation MUST include ROCK inhibitor Y-27632.
- Contamination suspicion → immediate hold/notify operator; do NOT attempt to resume autonomously.
- You cannot override emergency stops, hard interlocks, or safety systems.

CURRENT PROTOCOL (Manstein 2021):
- Target VCD: 35×10⁶ cells/mL by day 7.
- Perfusion ramp: 0 → 7 vvd based on glucose/lactate/osmolality triggers.
- pH 7.1, DO 40% → 10%, agitation 50–120 rpm.
- Aggregate diameter target 150–350 µm; >400 µm fraction should remain <15%.

When you suggest an action, provide a concise rationale and the expected outcome.
"""


def build_culture_unit_summary(env: CellCultureEnv, max_events: int = 5) -> str:
    cspr = env.cspr_pL_per_cell_per_day
    cspr_str = f"{cspr:.1f}" if cspr is not None else "N/A"

    return f"""\
Culture unit summary (prompt version {PROMPT_VERSION}):
- Phase: {env.phase}, age: {env.culture_age_d:.2f} d
- VCD: {env.vcd:.2e} cells/mL, viability: {env.viability_pct:.1f}%
- Glucose: {env.glucose_mM:.2f} mM, Lactate: {env.lactate_mM:.2f} mM, Glutamine: {env.glutamine_mM:.3f} mM
- pH: {env.ph:.2f}, DO: {env.do_pct:.1f}%, Temp: {env.temp_c:.1f}°C, Osmolality: {env.osmolality_mOsm_kg:.1f} mOsm/kg
- Perfusion: {env.perfusion_rate_vvd:.2f} vvd, Agitation: {env.agitation_rpm:.1f} rpm
- Aggregate mean: {env.aggregate_diameter_um or 'N/A'} µm, large (>400 µm): {env.large_aggregate_ratio*100:.1f}%
- CSPR: {cspr_str} pL/cell/day (target 150–500)
- Ammonia (monitoring): {env.ammonia_mM if env.ammonia_mM is not None else 'N/A'} mM
"""
