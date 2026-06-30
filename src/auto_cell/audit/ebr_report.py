"""EBR-like report builder for a run."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auto_cell.audit.audit_log import AuditLog
from auto_cell.audit.event_store import EventWriter
from auto_cell.schemas.audit_events import EventType


def build_ebr(base_dir: Path, run_id: str) -> dict[str, Any]:
    """Build a batch record summary for a run."""
    event_writer = EventWriter(base_dir)
    audit_log = AuditLog(base_dir)
    events = event_writer.load_run(run_id)
    report: dict[str, Any] = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_events": len(events),
            "commands": len([e for e in events if e.header.event_type == EventType.COMMAND]),
            "tool_executions": len([e for e in events if e.header.event_type == EventType.TOOL_EXEC]),
            "approvals": len([e for e in events if e.header.event_type == EventType.APPROVAL]),
        },
        "timeline": [e.model_dump(mode="json") for e in events],
        "audit_chain_valid": len(audit_log.verify(run_id)) == 0,
    }
    return report
