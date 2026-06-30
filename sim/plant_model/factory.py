"""Initial state factory for the Manstein plant model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .constants import MansteinConstants
from .state import Actuators, PlantState, Sensors

if TYPE_CHECKING:
    from auto_cell.plugins.cell_culture.environment import CellCultureEnv


def seed_state(
    seeding_density: float = 0.5e6,   # cells/mL
    viability: float = 97.0,          # %
    initial_glucose: float = 17.5,    # mM
    initial_glutamine: float = 2.0,   # mM
    initial_lactate: float = 0.0,     # mM
    initial_osmolality: float = 315.0, # mOsm/kg
    initial_aggregate_diameter: float = 50.0,  # µm
    constants: MansteinConstants | None = None,
) -> PlantState:
    """
    Manstein 2021 の single-cell inoculation 条件.
    150 mL DASbox, E8 + RI, 37°C, day 0 は perfusion なし.
    """
    return PlantState(
        vcd=seeding_density,
        viability=viability,
        glucose=initial_glucose,
        lactate=initial_lactate,
        glutamine=initial_glutamine,
        osmolality=initial_osmolality,
        aggregate_diameter=initial_aggregate_diameter,
    )


def sensors_to_env(sensors: Sensors, actuators: Actuators, culture_age_d: float = 0.0) -> "CellCultureEnv":  # noqa: F821
    """Convert plant_model Sensors + Actuators to a CellCultureEnv.

    Import is deferred to avoid a circular import at module load time.
    """
    from auto_cell.plugins.cell_culture.environment import CellCultureEnv

    return CellCultureEnv(
        vcd=sensors.vcd,
        viability_pct=sensors.viability,
        glucose_mM=sensors.glucose,
        lactate_mM=sensors.lactate,
        glutamine_mM=sensors.glutamine,
        ph=sensors.ph,
        do_pct=sensors.do_percent,
        temp_c=sensors.temp_c,
        osmolality_mOsm_kg=sensors.osmolality,
        aggregate_diameter_um=sensors.aggregate_diameter_um,
        perfusion_rate_vvd=actuators.perfusion_rate_vvd,
        agitation_rpm=actuators.agitation_rpm,
        do_setpoint_pct=actuators.do_setpoint,
        ph_setpoint=actuators.ph_setpoint,
        culture_age_d=culture_age_d,
        large_aggregate_ratio=0.0,
        phase="seed",
        media_volume_ml=150.0,
    )
