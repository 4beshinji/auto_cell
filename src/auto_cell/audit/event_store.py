"""Append-only JSONL event writer with fsync."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auto_cell._utils import validate_run_id
from auto_cell.schemas.audit_events import Event, EventHeader, EventType


class EventWriter:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)

    def _path_for(self, run_id: str) -> Path:
        validate_run_id(run_id)
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        dir_ = self.base_dir / run_id
        dir_.mkdir(parents=True, exist_ok=True)
        return dir_ / f"{day}.jsonl"

    def write(
        self,
        run_id: str,
        event_type: EventType,
        payload: dict[str, Any],
        *,
        source: str,
        actor: str,
        correlation_id: str | None = None,
        parent_event_id: str | None = None,
    ) -> Event:
        header = EventHeader(
            run_id=run_id,
            event_type=event_type,
            source=source,
            actor=actor,
            correlation_id=correlation_id,
            parent_event_id=parent_event_id,
        )
        event = Event(header=header, payload=payload)
        line = event.model_dump_json(ensure_ascii=False)
        path = self._path_for(run_id)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            os.fsync(f.fileno())
        return event

    def load_run(self, run_id: str) -> list[Event]:
        """Load all events for a run from all daily JSONL files."""
        validate_run_id(run_id)
        events: list[Event] = []
        dir_ = self.base_dir / run_id
        if not dir_.exists():
            return events
        for path in sorted(dir_.glob("*.jsonl")):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    events.append(Event.model_validate_json(line))
        return events
