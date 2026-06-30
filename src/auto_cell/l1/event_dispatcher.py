"""Normalize plugin events into active event names with suppression windows."""

from __future__ import annotations

from dataclasses import dataclass

from auto_cell.plugins.cell_culture.events import CultureEvent


@dataclass
class EventHistory:
    event: str
    first_seen_at_hours: float
    last_seen_at_hours: float
    count: int = 1


class EventDispatcher:
    """Apply suppression windows to raw CultureEvent streams."""

    def __init__(self, suppression_defaults: dict[str, float]):
        """Args: event_name -> suppression window in hours."""
        self.suppression_defaults = suppression_defaults
        self.active: dict[str, EventHistory] = {}

    def update(self, raw_events: list[CultureEvent], elapsed_hours: float) -> list[str]:
        seen_now = {e.event_id for e in raw_events}

        # Update existing active events that are still present.
        for name in seen_now:
            if name in self.active:
                self.active[name].last_seen_at_hours = elapsed_hours
                self.active[name].count += 1

        # Register newly seen events.
        for name in seen_now:
            if name not in self.active:
                self.active[name] = EventHistory(name, elapsed_hours, elapsed_hours)

        # Expire events outside their suppression window.
        def window_hours(name: str) -> float:
            return self.suppression_defaults.get(name, 0.0)

        expired = [
            name
            for name, hist in self.active.items()
            if elapsed_hours - hist.last_seen_at_hours > window_hours(name)
        ]
        for name in expired:
            del self.active[name]

        return list(self.active.keys())
