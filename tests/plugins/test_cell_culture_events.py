"""Tests for event detection."""

from typing import Any

from auto_cell.plugins.cell_culture.environment import CellCultureEnv
from auto_cell.plugins.cell_culture.events import detect_events


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


def test_no_events_in_normal_env():
    events = detect_events(_dummy_env())
    assert events == []


def test_detect_do_low():
    env = _dummy_env()
    env.do_pct = 7.5
    events = detect_events(env)
    assert any(e.event_id == "do_low" for e in events)


def test_large_aggregate_high():
    env = _dummy_env()
    env.large_aggregate_ratio = 0.18
    events = detect_events(env)
    assert any(e.event_id == "large_aggregate_high" for e in events)


def test_vcd_target_reached():
    env = _dummy_env(vcd=40.0e6)
    events = detect_events(env)
    assert any(e.event_id == "vcd_target_reached" for e in events)


def test_contamination_suspected():
    env = _dummy_env(contamination_suspected=True)
    events = detect_events(env)
    assert any(e.event_id == "contamination_suspected" for e in events)
