"""Tests for event dispatcher suppression."""

from __future__ import annotations

from auto_cell.l1.event_dispatcher import EventDispatcher
from auto_cell.plugins.cell_culture.events import CultureEvent


def make_event(event_id: str) -> CultureEvent:
    return CultureEvent(
        event_id=event_id,
        priority="P1",
        message=event_id,
        source_field="test",
        suppression_window_s=600,
    )


def test_active_event_persists_within_window():
    dispatcher = EventDispatcher({"glucose_low": 0.25})  # 15 min in hours
    active = dispatcher.update([make_event("glucose_low")], elapsed_hours=1.0)
    assert "glucose_low" in active
    active2 = dispatcher.update([], elapsed_hours=1.1)
    assert "glucose_low" in active2


def test_event_expires_after_window():
    dispatcher = EventDispatcher({"glucose_low": 0.25})
    dispatcher.update([make_event("glucose_low")], elapsed_hours=1.0)
    active = dispatcher.update([], elapsed_hours=1.3)
    assert "glucose_low" not in active


def test_new_event_registered():
    dispatcher = EventDispatcher({})
    active = dispatcher.update([make_event("lactate_high")], elapsed_hours=0.0)
    assert "lactate_high" in active
