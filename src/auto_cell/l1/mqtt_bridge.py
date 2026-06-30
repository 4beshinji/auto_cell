"""MQTT topic formatter and L1 gateway helpers."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from auto_cell.l1.types import ToolCall


_TOPIC_TEMPLATES: dict[str, str] = {
    "telemetry_single": "cell/{cu}/telemetry/{device_id}/{function_id}",
    "telemetry_all": "cell/{cu}/telemetry/{device_id}/all",
    "event": "cell/{cu}/event/{source}/{event_type}",
    "cmd": "cell/{cu}/cmd/{device_id}/{function_id}",
    "ack": "cell/{cu}/ack/{device_id}/{function_id}",
    "program_request": "cell/{cu}/program/{device_id}/request",
    "program_response": "cell/{cu}/program/{device_id}/response",
    "state_approval": "cell/{cu}/state/approval/{request_id}",
    "state_device": "cell/{cu}/state/device/{device_id}",
    "state_run": "cell/{cu}/state/run/{run_id}",
    "notify_hmi": "cell/{cu}/notify/hmi/{priority}",
    "hmi_approval": "cell/{cu}/hmi/approval/{request_id}",
    "hmi_command": "cell/{cu}/hmi/command/{command_name}",
}


def load_topic_templates(path: str | Path = "config/mqtt_topics.yaml") -> dict[str, str]:
    p = Path(path)
    if not p.exists():
        return _TOPIC_TEMPLATES
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return dict(data.get("topics", _TOPIC_TEMPLATES))


def format_topic(template_name: str, **kwargs: Any) -> str:
    template = _TOPIC_TEMPLATES.get(template_name, template_name)
    return template.format(**kwargs)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_TOOL_FUNCTION_MAP: dict[str, tuple[str, str]] = {
    "set_perfusion_rate": ("bioreactor_01", "set_perfusion_rate"),
    "set_agitation_rpm": ("bioreactor_01", "set_agitation_rpm"),
    "set_gas_setpoint": ("bioreactor_01", "set_gas_setpoint"),
    "feed": ("dispense_01", "feed"),
    "exchange_media": ("dispense_01", "exchange_media"),
    "trigger_passage": ("bioreactor_01", "trigger_passage"),
    "take_sample": ("sampler_01", "take_sample"),
}


def map_tool_to_function(tool: str) -> tuple[str, str]:
    return _TOOL_FUNCTION_MAP.get(tool, ("bioreactor_01", tool))


class L1MqttBridge:
    """Thin bridge between L1 ToolCalls and MQTT cmd/approval topics."""

    def __init__(self, culture_unit_id: str, broker_host: str, port: int = 1883) -> None:
        self.cu = culture_unit_id
        self.broker_host = broker_host
        self.port = port
        self._approval_callbacks: dict[str, Callable[[str], None]] = {}
        self._ack_callbacks: dict[str, Callable[[dict[str, Any]], None]] = {}

    def publish_cmd(
        self,
        tool_call: ToolCall,
        correlation_id: str | None = None,
        request_id: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        cid = correlation_id or f"c_{uuid.uuid4().hex}"
        rid = request_id or f"req_{uuid.uuid4().hex}"
        device_id, function_id = map_tool_to_function(tool_call.tool)
        topic = format_topic("cmd", cu=self.cu, device_id=device_id, function_id=function_id)
        payload = {
            "args": tool_call.args,
            "correlation_id": cid,
            "request_id": rid,
            "timestamp": utcnow_iso(),
            "source": "brain",
        }
        return topic, payload

    def request_approval(
        self,
        tool_call: ToolCall,
        correlation_id: str | None = None,
        request_id: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        rid = request_id or f"req_{uuid.uuid4().hex}"
        cid = correlation_id or f"c_{uuid.uuid4().hex}"
        topic = format_topic("state_approval", cu=self.cu, request_id=rid)
        payload = {
            "state": "requested",
            "request_id": rid,
            "correlation_id": cid,
            "requested_by": "l1_engine",
            "tool": tool_call.tool,
            "args": tool_call.args,
            "timestamp": utcnow_iso(),
        }
        return topic, payload

    def notify_hmi(self, priority: str, message: str, correlation_id: str | None = None) -> tuple[str, dict[str, Any]]:
        cid = correlation_id or f"c_{uuid.uuid4().hex}"
        topic = format_topic("notify_hmi", cu=self.cu, priority=priority)
        payload = {
            "priority": priority,
            "message": message,
            "source": "brain",
            "timestamp": utcnow_iso(),
            "correlation_id": cid,
        }
        return topic, payload
