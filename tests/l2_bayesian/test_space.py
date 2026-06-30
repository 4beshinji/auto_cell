"""Tests for CultureSearchSpace."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from auto_cell.l2_bayesian.space import CultureSearchSpace, PerfusionRampProfile


def _valid_space(**kwargs: float | str | PerfusionRampProfile) -> CultureSearchSpace:
    defaults: dict[str, float | str | PerfusionRampProfile] = {
        "seeding_density": 0.5e6,
        "initial_glucose_mm": 17.5,
        "perfusion_ramp_profile": PerfusionRampProfile.MANSTEIN_LINEAR,
        "max_perfusion_rate_vvd": 3.5,
        "agitation_base_rpm": 80,
        "do_transition_end_pct": 10.0,
        "y_27632_conc_um": 5.0,
    }
    defaults.update(kwargs)
    return CultureSearchSpace(**defaults)  # type: ignore[arg-type]


def test_to_ax_parameters_returns_list():
    space = _valid_space()
    params = space.to_ax_parameters()
    assert isinstance(params, list)
    names = {p["name"] for p in params}
    assert names == {
        "seeding_density",
        "initial_glucose_mm",
        "perfusion_ramp_profile",
        "max_perfusion_rate_vvd",
        "agitation_base_rpm",
        "do_transition_end_pct",
        "y_27632_conc_um",
    }


def test_conservative_max_perfusion_bound():
    with pytest.raises(ValidationError):
        _valid_space(
            perfusion_ramp_profile=PerfusionRampProfile.CONSERVATIVE,
            max_perfusion_rate_vvd=5.0,
        )


def test_aggressive_max_perfusion_allowed():
    space = _valid_space(
        perfusion_ramp_profile=PerfusionRampProfile.AGGRESSIVE,
        max_perfusion_rate_vvd=7.0,
    )
    assert space.perfusion_ramp_profile == PerfusionRampProfile.AGGRESSIVE
