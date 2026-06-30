"""Stub aggregation service for dashboard views."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from auto_cell.audit.event_store import EventWriter
from auto_cell.hmi.approval_service import ApprovalService
from auto_cell.schemas.audit_events import EventType, TelemetryPayload


def _normalize_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class DashboardService:
    def __init__(self, event_writer: EventWriter):
        self.event_writer = event_writer

    def run_status(self, run_id: str, approval_service: ApprovalService) -> dict[str, Any]:
        latest = self._latest_telemetry(run_id)
        return {
            "run_id": run_id,
            "phase": latest.get("phase", "unknown"),
            "cpp": {
                "vcd": latest.get("vcd"),
                "viability": latest.get("viability"),
                "glucose": latest.get("glucose"),
                "lactate": latest.get("lactate"),
                "ph": latest.get("ph"),
                "do": latest.get("do_percent"),
                "aggregate_diameter_um": latest.get("aggregate_diameter_um"),
            },
            "pending_approvals": len(approval_service.list_pending()),
        }

    def run_trend(
        self,
        run_id: str,
        channel: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict[str, Any]]:
        start_utc = _normalize_utc(start)
        end_utc = _normalize_utc(end)
        points: list[dict[str, Any]] = []
        for event in self.event_writer.load_run(run_id):
            if event.header.event_type != EventType.TELEMETRY:
                continue
            payload = event.payload
            if payload.get("channel") != channel:
                continue
            ts = _normalize_utc(event.header.timestamp)
            if start_utc and ts and ts < start_utc:
                continue
            if end_utc and ts and ts > end_utc:
                continue
            points.append({
                "timestamp": ts.isoformat() if ts else None,
                "value": payload.get("value"),
                "unit": payload.get("unit"),
                "quality": payload.get("quality"),
            })
        return points

    def run_events(self, run_id: str, limit: int = 100) -> list[dict[str, Any]]:
        events = self.event_writer.load_run(run_id)
        return [e.model_dump(mode="json") for e in events[-limit:]]

    def _latest_telemetry(self, run_id: str) -> dict[str, Any]:
        latest: dict[str, Any] = {}
        for event in self.event_writer.load_run(run_id):
            if event.header.event_type != EventType.TELEMETRY:
                continue
            channel = event.payload.get("channel")
            if channel:
                latest[channel] = event.payload.get("value")
        return latest

    def write_telemetry(self, run_id: str, payload: TelemetryPayload, actor: str = "system") -> None:
        self.event_writer.write(
            run_id=run_id,
            event_type=EventType.TELEMETRY,
            payload=payload.model_dump(mode="json"),
            source="dashboard_service",
            actor=actor,
        )
