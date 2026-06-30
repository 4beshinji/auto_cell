"""Merge and validate action candidates."""

from __future__ import annotations

from typing import Any

from auto_cell.l1.types import ActionCandidate, Context, ToolCall
from auto_cell.plugins.cell_culture.environment import CellCultureEnv
from auto_cell.plugins.cell_culture.sanitizer import validate_tool_call


ORDER = [
    "exchange_media",
    "set_perfusion_rate",
    "feed",
    "set_gas_setpoint",
    "set_agitation_rpm",
    "trigger_passage",
    "take_sample",
    "notify",
    "log",
]


class ActionPlanner:
    """Resolve refs, expand virtual tools, validate, and order action candidates."""

    def plan(
        self,
        candidates: list[ActionCandidate],
        env: CellCultureEnv,
        state_id: str,
        context: Context | None = None,
    ) -> tuple[list[ToolCall], list[ToolCall], list[ToolCall]]:
        executed: list[ToolCall] = []
        rejected: list[ToolCall] = []
        approval_requested: list[ToolCall] = []

        seen_tools: set[str] = set()

        for cand in candidates:
            tool = cand.action.tool
            if tool in seen_tools and tool not in {"notify", "log", "feed"}:
                continue
            seen_tools.add(tool)

            action = self._normalize_action(cand.action, context)

            if action.tool in {"notify", "log"}:
                executed.append(action)
                continue

            result, reason = validate_tool_call(env, action.tool, action.args)
            if result == "rejected":
                rejected.append(action)
                continue
            if result == "approval_required":
                approval_requested.append(action)
                continue

            executed.append(action)

        executed.sort(key=lambda tc: ORDER.index(tc.tool) if tc.tool in ORDER else 99)
        return executed, rejected, approval_requested

    def _normalize_action(self, action: ToolCall, context: Context | None) -> ToolCall:
        args = dict(action.args)
        tool = action.tool

        if tool == "ramp_perfusion":
            return self._expand_ramp(args, context)

        if tool == "set_perfusion_rate":
            if "rate_ref" in args and context is not None:
                args["vvd"] = context.resolve(args.pop("rate_ref"))
            elif "rate" in args:
                args["vvd"] = args.pop("rate")
            args.pop("unit", None)

        elif tool == "set_agitation_rpm":
            if "rpm_ref" in args and context is not None:
                args["rpm"] = context.resolve(args.pop("rpm_ref"))

        elif tool == "set_gas_setpoint":
            if "parameter" in args:
                args["gas"] = args.pop("parameter")
            if "setpoint_ref" in args and context is not None:
                args["setpoint"] = context.resolve(args.pop("setpoint_ref"))
            elif "value_ref" in args and context is not None:
                args["setpoint"] = context.resolve(args.pop("value_ref"))
            elif "value" in args:
                args["setpoint"] = args.pop("value")

        elif tool == "feed":
            if "substance" in args:
                substance = args.pop("substance")
                args.setdefault("media_id", substance)
                if "target_bump_mM" in args and "concentration_mM" in args:
                    bump = float(args.pop("target_bump_mM"))
                    conc = float(args["concentration_mM"])
                    volume_ml = 1.0 if conc <= 0 else bump / conc
                    args["volume_ml"] = volume_ml
                else:
                    args.setdefault("volume_ml", 1.0)
                args.pop("concentration_mM", None)

        elif tool == "trigger_passage":
            if "rock_inhibitor_conc_uM_ref" in args and context is not None:
                args["rock_inhibitor_conc_uM"] = context.resolve(
                    args.pop("rock_inhibitor_conc_uM_ref")
                )

        return ToolCall(tool=tool, args=args)

    def _expand_ramp(self, args: dict[str, Any], context: Context | None) -> ToolCall:
        if context is None:
            return ToolCall(tool="set_perfusion_rate", args={"vvd": 0.0})
        start_h = float(self._resolve_arg(args.get("start_h_ref"), context))
        end_h = float(self._resolve_arg(args.get("end_h_ref"), context))
        start_rate = float(args.get("start_rate", 0.0))
        end_rate = float(self._resolve_arg(args.get("end_rate_ref"), context))
        elapsed = context.elapsed_hours
        if elapsed <= start_h:
            rate = start_rate
        elif elapsed >= end_h:
            rate = end_rate
        else:
            ratio = (elapsed - start_h) / (end_h - start_h)
            rate = start_rate + (end_rate - start_rate) * ratio
        return ToolCall(tool="set_perfusion_rate", args={"vvd": rate})

    def _resolve_arg(self, value: Any, context: Context) -> Any:
        if isinstance(value, str):
            try:
                return context.resolve(value)
            except ValueError:
                return value
        return value
