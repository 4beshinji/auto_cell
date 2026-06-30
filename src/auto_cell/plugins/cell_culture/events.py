"""Event detection for cell_culture plugin."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from auto_cell.plugins.cell_culture.environment import CellCultureEnv, CppEnvelope

Priority = Literal["P0", "P1", "P2", "P3"]


@dataclass(frozen=True)
class CultureEvent:
    event_id: str
    priority: Priority
    message: str
    source_field: str
    measured_at: datetime | None = None
    # 抑制用情報（呼び出し側で利用）
    suppression_window_s: int = 300


def event_descriptions() -> dict[str, str]:
    return {
        "ph_out_of_range": "pH が早期警戒範囲を逸脱（6.95–7.25）。",
        "do_low": "溶存酸素（DO）が早期警戒下限（8%）以下。",
        "lactate_high": "乳酸が早期警戒値（35 mM）以上。",
        "glucose_low": "グルコースが早期警戒値（1.8 mM）以下。",
        "glutamine_low": "グルタミンが早期警戒値（0.008 mM）以下。",
        "osmolality_high": "浸透圧が早期警戒値（450 mOsm/kg）以上。",
        "aggregate_out_of_range": "凝集体平均径が目標範囲外（150–350 µm）。",
        "large_aggregate_high": "大径凝集体（>400 µm）割合が高い（>15%）。",
        "vcd_target_reached": "目標 VCD（35×10⁶/mL）に到達。継代判断の起点。",
        "contamination_suspected": "無菌性逸脱が検知された。即時ホールド。",
        "shear_risk": "撹拌が高シア領域（≥140 rpm）に入った。",
    }


def suppression_defaults() -> dict[str, float]:
    """Return event name -> suppression window in hours.

    These windows are consumed by ``EventDispatcher``, which tracks
    ``elapsed_hours``. The companion ``CultureEvent.suppression_window_s``
    field remains in seconds for downstream HMI/push consumers that expect
    wall-clock units.
    """
    return {
        "ph_out_of_range": 300 / 3600.0,
        "do_low": 300 / 3600.0,
        "lactate_high": 600 / 3600.0,
        "glucose_low": 300 / 3600.0,
        "glutamine_low": 600 / 3600.0,
        "osmolality_high": 600 / 3600.0,
        "aggregate_out_of_range": 600 / 3600.0,
        "large_aggregate_high": 600 / 3600.0,
        "vcd_target_reached": 3600 / 3600.0,
        "contamination_suspected": 0.0,
        "shear_risk": 300 / 3600.0,
    }


def _make(event_id: str, priority: Priority, field_name: str, now: datetime) -> CultureEvent:
    return CultureEvent(
        event_id=event_id,
        priority=priority,
        message=event_descriptions()[event_id],
        source_field=field_name,
        measured_at=now,
        suppression_window_s=int(suppression_defaults()[event_id] * 3600),
    )


def detect_events(env: CellCultureEnv, now: datetime | None = None) -> list[CultureEvent]:
    if now is None:
        now = env.measured_at
    events: list[CultureEvent] = []
    e = CppEnvelope

    if env.ph < e.PH_WARNING[0] or env.ph > e.PH_WARNING[1]:
        events.append(_make("ph_out_of_range", "P1", "ph", now))

    if env.do_pct <= e.DO_WARNING[0]:
        events.append(_make("do_low", "P1", "do_pct", now))

    if env.lactate_mM >= e.LACTATE_WARNING:
        events.append(_make("lactate_high", "P1", "lactate_mM", now))

    if env.glucose_mM <= e.GLUCOSE_WARNING:
        events.append(_make("glucose_low", "P1", "glucose_mM", now))

    if env.glutamine_mM <= e.GLUTAMINE_WARNING:
        events.append(_make("glutamine_low", "P1", "glutamine_mM", now))

    if env.osmolality_mOsm_kg >= e.OSMOLALITY_WARNING:
        events.append(_make("osmolality_high", "P1", "osmolality_mOsm_kg", now))

    if env.aggregate_diameter_um is not None:
        d = env.aggregate_diameter_um
        if d < e.AGGREGATE_MEAN_WARNING[0] or d > e.AGGREGATE_MEAN_WARNING[1]:
            events.append(_make("aggregate_out_of_range", "P2", "aggregate_diameter_um", now))

    if env.large_aggregate_ratio >= e.LARGE_AGGREGATE_WARNING:
        events.append(_make("large_aggregate_high", "P2", "large_aggregate_ratio", now))

    if env.vcd >= e.VCD_PASSAGE_TARGET:
        events.append(_make("vcd_target_reached", "P2", "vcd", now))

    # contamination_suspected は env には bool フィールドを持たない想定。
    # L1 サイクルは device からの discrete channel をこのイベントに直接マッピングする。
    # ここでは env に含まれる場合のみ検出する便宜上の例（実装時は channel 側で制御）。
    if getattr(env, "contamination_suspected", False):
        events.append(_make("contamination_suspected", "P0", "contamination_suspected", now))

    if env.agitation_rpm >= e.AGITATION_WARNING[1]:
        events.append(_make("shear_risk", "P2", "agitation_rpm", now))

    return sorted(events, key=lambda ev: (ev.priority, ev.event_id))
