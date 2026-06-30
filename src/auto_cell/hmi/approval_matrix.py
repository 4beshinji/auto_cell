"""Approval matrix: tool/condition -> approval need, timeout, safe default."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Decision:
    requires_approval: bool
    timeout_sec: float
    safe_default: str


class ApprovalMatrix:
    def __init__(self, path: str | Path):
        self._path = Path(path)
        with open(self._path, encoding="utf-8") as f:
            self._rules = yaml.safe_load(f) or {}

    def decide(self, tool_name: str, params: dict[str, Any], run_context: dict[str, Any]) -> Decision:
        run_id = run_context.get("run_id", "")
        _ = run_id
        rule = self._rules.get(
            tool_name,
            {"requires_approval": True, "timeout_sec": 600, "safe_default": "cancel"},
        )
        envelope = rule.get("envelope", {})

        if tool_name == "set_perfusion_rate":
            vvd = params.get("vvd", 0.0)
            vvd_range = envelope.get("vvd")
            if vvd_range and vvd_range[0] <= vvd <= vvd_range[1]:
                return Decision(False, 0.0, rule.get("safe_default", "cancel"))

        if tool_name == "set_agitation_rpm":
            rpm = params.get("rpm", 0.0)
            rpm_range = envelope.get("rpm")
            if rpm_range and rpm_range[0] <= rpm <= rpm_range[1]:
                return Decision(False, 0.0, rule.get("safe_default", "cancel"))

        if tool_name == "set_gas_setpoint":
            gas = params.get("gas")
            setpoint = params.get("setpoint", 0.0)
            gas_envelope = envelope.get(gas)
            if gas_envelope and gas_envelope[0] <= setpoint <= gas_envelope[1]:
                return Decision(False, 0.0, rule.get("safe_default", "cancel"))

        if tool_name == "feed":
            volume_ml = params.get("volume_ml", 0.0)
            max_volume = envelope.get("max_volume_ml")
            if max_volume is not None and volume_ml <= max_volume:
                return Decision(False, 0.0, rule.get("safe_default", "cancel"))

        if tool_name == "exchange_media":
            volume_ml = params.get("volume_ml", 0.0)
            max_volume = envelope.get("max_volume_ml")
            if max_volume is not None and volume_ml <= max_volume:
                return Decision(False, 0.0, rule.get("safe_default", "cancel"))

        if tool_name == "adjust_setpoint":
            channel = params.get("channel")
            value = params.get("value", 0.0)
            channel_envelope = envelope.get(channel)
            if channel_envelope and channel_envelope[0] <= value <= channel_envelope[1]:
                return Decision(False, 0.0, rule.get("safe_default", "cancel"))

        if tool_name == "take_sample":
            return Decision(False, 0.0, rule.get("safe_default", "cancel"))

        return Decision(
            rule.get("requires_approval", True),
            rule.get("timeout_sec", 600),
            rule.get("safe_default", "cancel"),
        )
