"""Tool schemas and handlers for cell_culture plugin."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ToolResult:
    status: str  # "accepted", "rejected", "queued_for_approval"
    requested_actuators: dict[str, Any]
    audit_note: str
    correlation_id: str | None = None


TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "set_perfusion_rate": {
        "description": "Set the perfusion rate in vessel volumes per day (vvd).",
        "parameters": {
            "type": "object",
            "properties": {
                "vvd": {"type": "number", "minimum": 0.0, "maximum": 7.0},
                "ramp_duration_s": {"type": "integer", "minimum": 0},
            },
            "required": ["vvd"],
        },
    },
    "set_agitation_rpm": {
        "description": "Set the agitation speed.",
        "parameters": {
            "type": "object",
            "properties": {
                "rpm": {"type": "number", "minimum": 0.0, "maximum": 150.0},
            },
            "required": ["rpm"],
        },
    },
    "feed": {
        "description": "Bolus feed of glucose/glutamine media.",
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {"type": "string"},
                "volume_ml": {"type": "number", "minimum": 0.0},
                "glucose_mM": {"type": "number", "minimum": 0.0},
                "glutamine_mM": {"type": "number", "minimum": 0.0},
            },
            "required": ["media_id", "volume_ml"],
        },
    },
    "exchange_media": {
        "description": "Perform a media exchange (perfusion-like bolus).",
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {"type": "string"},
                "volume_ml": {"type": "number", "minimum": 0.0},
            },
            "required": ["media_id", "volume_ml"],
        },
    },
    "set_gas_setpoint": {
        "description": "Set a gas loop setpoint (DO or pH/CO2).",
        "parameters": {
            "type": "object",
            "properties": {
                "gas": {"type": "string", "enum": ["do", "co2", "o2", "ph"]},
                "setpoint": {"type": "number"},
            },
            "required": ["gas", "setpoint"],
        },
    },
    "trigger_passage": {
        "description": "Dissociate aggregates and reseed. Y-27632 is mandatory.",
        "parameters": {
            "type": "object",
            "properties": {
                "method": {"type": "string", "enum": ["dissociate", "dilute", "split"]},
                "target_vcd": {"type": "number", "minimum": 0.0},
                "add_rock_inhibitor": {"type": "boolean"},
                "rock_inhibitor_conc_uM": {"type": "number", "minimum": 0.0},
            },
            "required": ["method", "add_rock_inhibitor"],
        },
    },
    "take_sample": {
        "description": "Withdraw a sample for at-line analytics.",
        "parameters": {
            "type": "object",
            "properties": {
                "volume_ml": {"type": "number", "minimum": 0.0, "maximum": 50.0},
                "purpose": {"type": "string"},
            },
            "required": ["volume_ml"],
        },
    },
}


def tool_schemas() -> dict[str, dict[str, Any]]:
    return TOOL_SCHEMAS


def _handle_set_perfusion_rate(args: dict[str, Any]) -> ToolResult:
    return ToolResult(
        status="accepted",
        requested_actuators={"perfusion_rate_vvd": args["vvd"]},
        audit_note=f"Request perfusion rate {args['vvd']} vvd",
    )


def _handle_set_agitation_rpm(args: dict[str, Any]) -> ToolResult:
    return ToolResult(
        status="accepted",
        requested_actuators={"agitation_rpm": args["rpm"]},
        audit_note=f"Request agitation {args['rpm']} rpm",
    )


def _handle_feed(args: dict[str, Any]) -> ToolResult:
    return ToolResult(
        status="accepted",
        requested_actuators={
            "feed_volume_ml": args["volume_ml"],
            "feed_media_id": args["media_id"],
            "feed_glucose_mM": args.get("glucose_mM", 0.0),
            "feed_glutamine_mM": args.get("glutamine_mM", 0.0),
        },
        audit_note=f"Feed {args['volume_ml']} mL of {args['media_id']}",
    )


def _handle_exchange_media(args: dict[str, Any]) -> ToolResult:
    return ToolResult(
        status="accepted",
        requested_actuators={
            "exchange_volume_ml": args["volume_ml"],
            "exchange_media_id": args["media_id"],
        },
        audit_note=f"Exchange {args['volume_ml']} mL media to {args['media_id']}",
    )


def _handle_set_gas_setpoint(args: dict[str, Any]) -> ToolResult:
    gas = args["gas"]
    setpoint = args["setpoint"]
    actuator_key = {"do": "do_setpoint_pct", "co2": "co2_setpoint_pct", "ph": "ph_setpoint"}.get(gas, f"{gas}_setpoint")
    return ToolResult(
        status="accepted",
        requested_actuators={actuator_key: setpoint},
        audit_note=f"Set {gas} setpoint to {setpoint}",
    )


def _handle_trigger_passage(args: dict[str, Any]) -> ToolResult:
    return ToolResult(
        status="accepted",
        requested_actuators={
            "passage_method": args["method"],
            "passage_target_vcd": args.get("target_vcd"),
            "add_rock_inhibitor": args["add_rock_inhibitor"],
            "rock_inhibitor_conc_uM": args.get("rock_inhibitor_conc_uM", 10.0),
        },
        audit_note=f"Trigger passage method={args['method']} Y-27632={args['add_rock_inhibitor']}",
    )


def _handle_take_sample(args: dict[str, Any]) -> ToolResult:
    return ToolResult(
        status="accepted",
        requested_actuators={
            "sample_volume_ml": args["volume_ml"],
            "sample_purpose": args.get("purpose", "at-line"),
        },
        audit_note=f"Take {args['volume_ml']} mL sample",
    )


ToolHandler = Callable[[dict[str, Any]], ToolResult]


def tool_handlers() -> dict[str, ToolHandler]:
    return {
        "set_perfusion_rate": _handle_set_perfusion_rate,
        "set_agitation_rpm": _handle_set_agitation_rpm,
        "feed": _handle_feed,
        "exchange_media": _handle_exchange_media,
        "set_gas_setpoint": _handle_set_gas_setpoint,
        "trigger_passage": _handle_trigger_passage,
        "take_sample": _handle_take_sample,
    }


def invoke_tool(name: str, args: dict[str, Any]) -> ToolResult:
    handler = tool_handlers().get(name)
    if handler is None:
        return ToolResult(status="rejected", requested_actuators={}, audit_note=f"Unknown tool {name}")
    return handler(args)
