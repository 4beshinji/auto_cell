"""Tests for CellCultureEnv and CppEnvelope."""

from typing import Any

import pytest

from auto_cell.plugins.cell_culture.environment import CellCultureEnv


def _dummy_env(**kwargs: Any) -> CellCultureEnv:
    defaults: dict[str, Any] = {
        "vcd": 1.0e6,
        "viability_pct": 95.0,
        "glucose_mM": 5.0,
        "lactate_mM": 10.0,
        "glutamine_mM": 0.1,
        "ph": 7.1,
        "do_pct": 40.0,
        "temp_c": 37.0,
        "osmolality_mOsm_kg": 320.0,
        "agitation_rpm": 80.0,
    }
    defaults.update(kwargs)
    return CellCultureEnv(**defaults)


def test_cspr_computation():
    env = _dummy_env(vcd=35e6, perfusion_rate_vvd=7.0)
    assert env.cspr_pL_per_cell_per_day == 7.0 / 35e6 * 1e9
    assert env.cspr_status == "ok"


def test_cspr_low():
    env = _dummy_env(vcd=35e6, perfusion_rate_vvd=1.0)
    assert env.cspr_status == "low"


def test_cspr_high():
    env = _dummy_env(vcd=1e6, perfusion_rate_vvd=7.0)
    assert env.cspr_status == "high"


def test_viability_range():
    with pytest.raises(ValueError):
        _dummy_env(viability_pct=101.0)


def test_ph_range():
    with pytest.raises(ValueError):
        _dummy_env(ph=14.5)
