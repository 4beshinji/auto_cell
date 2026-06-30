"""BO search-space definition. Aligned with `kg_to_auto_cell.md` §4 CPP envelope."""

from __future__ import annotations

from enum import Enum
from typing import Any, Self

from pydantic import BaseModel, Field, model_validator


class PerfusionRampProfile(str, Enum):
    """Perfusion rate 0→max schedule shape.

    Phase 1 uses discrete profiles; the L1 state machine/recipe expands them
    into a time-series schedule. Continuous parameterization is left to Phase 2.
    """

    MANSTEIN_LINEAR = "manstein_linear"  # 0→max linearly over culture days
    CONSERVATIVE = "conservative"        # gentler ramp
    AGGRESSIVE = "aggressive"            # faster ramp


class CultureSearchSpace(BaseModel):
    """Design variables for one run. Ranges are tentative operating windows."""

    seeding_density: float = Field(
        ..., ge=0.2e6, le=2.0e6, description="cells/mL"
    )
    initial_glucose_mm: float = Field(..., ge=10.0, le=30.0)
    perfusion_ramp_profile: PerfusionRampProfile
    max_perfusion_rate_vvd: float = Field(..., ge=0.0, le=7.0)
    agitation_base_rpm: int = Field(..., ge=30, le=150)
    do_transition_end_pct: float = Field(
        ..., ge=5.0, le=15.0, description="DO setpoint ramped from 40% to this value"
    )
    y_27632_conc_um: float = Field(..., ge=0.0, le=10.0)

    @model_validator(mode="after")
    def _profile_bound(self) -> Self:
        profile_max = {
            PerfusionRampProfile.CONSERVATIVE: 4.0,
            PerfusionRampProfile.MANSTEIN_LINEAR: 7.0,
            PerfusionRampProfile.AGGRESSIVE: 7.0,
        }[self.perfusion_ramp_profile]
        if self.max_perfusion_rate_vvd > profile_max:
            raise ValueError(
                f"{self.perfusion_ramp_profile.value} max_perfusion_rate must be <= "
                f"{profile_max} vvd"
            )
        return self

    def to_ax_parameters(self) -> list[dict[str, Any]]:
        """Return Ax-compatible parameter definitions for `AxClient.create_experiment`."""
        return [
            {
                "name": "seeding_density",
                "type": "range",
                "bounds": [0.2e6, 2.0e6],
                "value_type": "float",
            },
            {
                "name": "initial_glucose_mm",
                "type": "range",
                "bounds": [10.0, 30.0],
                "value_type": "float",
            },
            {
                "name": "perfusion_ramp_profile",
                "type": "choice",
                "values": [e.value for e in PerfusionRampProfile],
                "value_type": "str",
            },
            {
                "name": "max_perfusion_rate_vvd",
                "type": "range",
                "bounds": [0.0, 7.0],
                "value_type": "float",
            },
            {
                "name": "agitation_base_rpm",
                "type": "range",
                "bounds": [30, 150],
                "value_type": "int",
            },
            {
                "name": "do_transition_end_pct",
                "type": "range",
                "bounds": [5.0, 15.0],
                "value_type": "float",
            },
            {
                "name": "y_27632_conc_um",
                "type": "range",
                "bounds": [0.0, 10.0],
                "value_type": "float",
            },
        ]
