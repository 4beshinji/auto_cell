"""Tests for audit/event store schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from auto_cell.schemas.audit_events import (
    ApprovalPayload,
    CommandPayload,
    Event,
    EventHeader,
    EventType,
    TelemetryPayload,
)


def test_event_header_rejects_extra_fields():
    with pytest.raises(ValidationError):
        EventHeader(
            run_id="run_001",
            source="test",
            actor="system",
            event_type=EventType.TELEMETRY,
            extra_field="not_allowed",
        )


def test_event_header_is_frozen():
    header = EventHeader(
        run_id="run_001",
        source="test",
        actor="system",
        event_type=EventType.TELEMETRY,
    )
    with pytest.raises(ValidationError):
        header.source = "other"


def test_event_rejects_extra_fields():
    header = EventHeader(
        run_id="run_001",
        source="test",
        actor="system",
        event_type=EventType.TELEMETRY,
    )
    with pytest.raises(ValidationError):
        Event(header=header, payload={"value": 1.0}, extra="bad")


def test_command_payload_requires_request_id():
    with pytest.raises(ValidationError):
        CommandPayload(tool_name="feed", args={"volume_ml": 1.0})


def test_approval_payload_state_literal():
    with pytest.raises(ValidationError):
        ApprovalPayload(
            request_id="req_1",
            tool_name="feed",
            params={},
            state="invalid_state",
            requested_by="system",
            timeout_sec=600,
        )


def test_approval_payload_safe_default_literal():
    with pytest.raises(ValidationError):
        ApprovalPayload(
            request_id="req_1",
            tool_name="feed",
            params={},
            state="requested",
            requested_by="system",
            timeout_sec=600,
            safe_default="invalid",
        )


def test_telemetry_payload_quality_literal():
    with pytest.raises(ValidationError):
        TelemetryPayload(channel="vcd", value=1.0, quality="unknown")
