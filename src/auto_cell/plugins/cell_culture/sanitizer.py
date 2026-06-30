"""Tool-call validation: envelope, ramp limits, Y-27632 enforcement."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from auto_cell.plugins.cell_culture.environment import CellCultureEnv, CppEnvelope, RampLimits
from auto_cell.plugins.cell_culture.tools import TOOL_SCHEMAS

ValidationResult = Literal["accepted", "approval_required", "rejected"]


def _hours_since(dt: datetime | None) -> float | None:
    if dt is None:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0


def _check_ramp(current: float, target: float, last: float | None, last_at: datetime | None, limit_per_hour: float) -> ValidationResult:
    if last is None or last_at is None:
        return "accepted"
    delta = abs(target - last)
    hours = _hours_since(last_at)
    if hours is None or hours <= 0.0:
        # 同一周期内の重複は拒否
        return "rejected" if delta > 1e-9 else "accepted"
    if delta / hours > limit_per_hour:
        return "rejected"
    return "accepted"


def validate_tool_call(
    env: CellCultureEnv,
    tool_name: str,
    args: dict[str, Any],
    now: datetime | None = None,
) -> tuple[ValidationResult, str]:
    """Return (result, reason)."""
    now = now or datetime.now(timezone.utc)
    e = CppEnvelope

    # 未知ツール
    if tool_name not in TOOL_SCHEMAS:
        return "rejected", f"Unknown tool: {tool_name}"

    # --- set_perfusion_rate ---
    if tool_name == "set_perfusion_rate":
        vvd = args["vvd"]
        if vvd < e.PERFUSION_LIMIT[0] or vvd > e.PERFUSION_LIMIT[1]:
            # 灌流上限は 7 vvd（Manstein）を超えたら承認要求
            return "approval_required", f"Perfusion {vvd} vvd outside validated envelope {e.PERFUSION_LIMIT[0]}–{e.PERFUSION_LIMIT[1]} vvd"
        ramp = _check_ramp(
            env.perfusion_rate_vvd, vvd, env.last_perfusion_rate_vvd, env.last_setpoint_at, RampLimits.PERFUSION_VVD_PER_HOUR
        )
        if ramp == "rejected":
            return "rejected", f"Perfusion ramp exceeds {RampLimits.PERFUSION_VVD_PER_HOUR} vvd/h"
        return "accepted", ""

    # --- set_agitation_rpm ---
    if tool_name == "set_agitation_rpm":
        rpm = args["rpm"]
        if rpm < e.AGITATION_LIMIT[0] or rpm > e.AGITATION_LIMIT[1]:
            return "approval_required", f"Agitation {rpm} rpm outside limit 30–150 rpm"
        ramp = _check_ramp(
            env.agitation_rpm, rpm, env.last_agitation_rpm, env.last_setpoint_at, RampLimits.AGITATION_RPM_PER_HOUR
        )
        if ramp == "rejected":
            return "rejected", f"Agitation ramp exceeds {RampLimits.AGITATION_RPM_PER_HOUR} rpm/h"
        return "accepted", ""

    # --- set_gas_setpoint ---
    if tool_name == "set_gas_setpoint":
        gas = args["gas"]
        sp = args["setpoint"]
        if gas == "do":
            if sp < e.DO_LIMIT[0] or sp > e.DO_LIMIT[1]:
                return "approval_required", f"DO setpoint {sp}% outside 5–50%"
            ramp = _check_ramp(
                env.do_pct, sp, env.last_do_setpoint_pct, env.last_setpoint_at, RampLimits.DO_PCT_PER_HOUR
            )
            if ramp == "rejected":
                return "rejected", f"DO ramp exceeds {RampLimits.DO_PCT_PER_HOUR}%/h"
        elif gas == "ph":
            if sp < e.PH_LIMIT[0] or sp > e.PH_LIMIT[1]:
                return "approval_required", f"pH setpoint {sp} outside 6.9–7.3"
            ramp = _check_ramp(
                env.ph, sp, env.last_ph_setpoint, env.last_setpoint_at, RampLimits.PH_PER_HOUR
            )
            if ramp == "rejected":
                return "rejected", f"pH ramp exceeds {RampLimits.PH_PER_HOUR}/h"
        return "accepted", ""

    # --- trigger_passage ---
    if tool_name == "trigger_passage":
        if not args.get("add_rock_inhibitor", False):
            return "rejected", "trigger_passage requires add_rock_inhibitor=True (Y-27632)"
        if args.get("method", "dissociate") != "dissociate":
            return "approval_required", f"Passage method {args.get('method')} not validated in v1"
        # 目標密度未満で継代を要求する場合は承認対象
        if env.vcd < e.VCD_PASSAGE_TARGET * 0.5:
            return "approval_required", f"VCD {env.vcd} too low for passage (<50% target)"
        return "accepted", ""

    # --- feed / exchange_media / take_sample ---
    # 量の明らかな過剰のみ拒否。包絡線外のメディア ID は承認対象。
    if tool_name in {"feed", "exchange_media"}:
        vol = args["volume_ml"]
        if vol > env.media_volume_ml:
            return "rejected", f"Volume {vol} mL exceeds working volume {env.media_volume_ml} mL"
        return "accepted", ""

    if tool_name == "take_sample":
        vol = args["volume_ml"]
        if vol > env.media_volume_ml * 0.2:
            return "approval_required", f"Sample {vol} mL > 20% working volume"
        return "accepted", ""

    return "accepted", ""
