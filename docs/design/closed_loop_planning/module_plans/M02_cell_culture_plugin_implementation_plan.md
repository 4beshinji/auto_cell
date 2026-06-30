# M02 `cell_culture` ドメインプラグイン詳細実装計画

> Scope: auto_cell A 層 Phase 1 — iPSC 浮遊/凝集体バイオリアクター制御（Manstein 型灌流 0→7 vvd）
> 対象ディレクトリ: `src/auto_cell/plugins/cell_culture/`
> 前提文書: `05_implementation_plan_phase1.md`, `06_critical_path_and_work_order.md`, `03_swarm_findings_integration.md`, `02_missing_assets_for_closed_loop.md`, `docs/design/kg_to_auto_cell.md`, `src/auto_cell/plugins/cell_culture/__init__.py`

---

## 1. ファイル構成

`plugins/cell_culture/` 以下に以下のモジュールを作成する。

| # | ファイル | 責務 | Phase 1 完了基準 |
|---|---|---|---|
| 1 | `__init__.py` | `CellCulturePlugin` クラスのエクスポート、`plugin_class` 登録 | import 成功、ABC/仮 IF への適合 |
| 2 | `environment.py` | `CellCultureEnv` Pydantic model、CPP 包絡線定数、CSPR 計算 | `tests/plugins/test_cell_culture_env.py` pass |
| 3 | `channels.py` | `channel_config`, `route_channel`、LADS Function 名対応 | 全 channel の mapping テスト pass |
| 4 | `events.py` | 全イベント判定ロジック、抑制窓、優先度 | 全イベントの閾値/抑制テスト pass |
| 5 | `tools.py` | 副作用ツールの JSON schema と handler | 各ツールのシリアライズ/実行テスト pass |
| 6 | `sanitizer.py` | `validate_tool_call`（包絡線・ramp・Y-27632 強制） | 拒否/承認パターンのテスト pass |
| 7 | `prompt.py` | L3 LLM 用システムプロンプトと状態要約関数 | プロンプト文字列生成テスト pass |
| 8 | `confidence.py` | 信頼度スコア層の骨格 | GP/PLS/DL 各タイプのスケルトン呼び出し pass |
| 9 | `aggregate_imaging.py` | Cellpose 統合、凝集体メトリクス算出 | ダミー画像/segment テスト pass |

---

## 2. `environment.py` — `CellCultureEnv` Pydantic model

### 2.1 設計方針

- `CellCultureEnv` は A 層の「培養単位あたりの世界モデル」に対応する。
- 全 CPP を型付きフィールドで保持する。
- **CSPR は計算フィールド**とし、S02 の作業範囲 150–500 pL/cell/day を超過した場合に HMI アドバイザリを出せるようにする。
- **アンモニアは参考監視値**とし、現時点ではイベント化しない（S02 判断）。
- **large_aggregate_ratio** は画像解析またはデバイス analog 出力から得た「>400 µm 凝集体の体積/面積割合」とする。
- ramp 制限判定に必要な「前回 setpoint + 時刻」を `last_*` フィールドで保持する。

### 2.2 コード

```python
# src/auto_cell/plugins/cell_culture/environment.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, computed_field, model_validator

CulturePhase = Literal[
    "seed",
    "perfusion_ramp",
    "production",
    "passage_ready",
    "passage_executing",
    "hold",
    "contamination_hold",
]


class CellCultureEnv(BaseModel):
    """iPSC 浮遊/凝集体バイオリアクターの状態表現（A 層 WorldModel）。"""

    # --- 細胞 ---
    vcd: float = Field(..., ge=0.0, description="Viable cell density [cells/mL]")
    viability_pct: float = Field(..., ge=0.0, le=100.0, description="Cell viability [%]")

    # --- 代謝物 ---
    glucose_mM: float = Field(..., ge=0.0, description="Glucose [mM]")
    lactate_mM: float = Field(..., ge=0.0, description="Lactate [mM]")
    glutamine_mM: float = Field(..., ge=0.0, description="Glutamine [mM]")
    ammonia_mM: float | None = Field(
        default=None, ge=0.0, description="Ammonia [mM] — monitoring reference only (S02)"
    )

    # --- 環境 ---
    ph: float = Field(..., ge=0.0, le=14.0, description="Culture pH")
    do_pct: float = Field(..., ge=0.0, le=150.0, description="Dissolved oxygen [% air sat]")
    co2_pct: float | None = Field(default=None, ge=0.0, le=100.0, description="CO2 [%]")
    temp_c: float = Field(..., ge=30.0, le=45.0, description="Temperature [°C]")
    osmolality_mOsm_kg: float = Field(..., ge=0.0, description="Osmolality [mOsm/kg]")

    # --- アクチュエータ状態（現在値） ---
    perfusion_rate_vvd: float = Field(0.0, ge=0.0, le=20.0, description="Perfusion rate [vvd]")
    agitation_rpm: float = Field(..., ge=0.0, le=500.0, description="Agitation [rpm]")
    do_setpoint_pct: float | None = Field(default=None, ge=0.0, le=150.0)
    ph_setpoint: float | None = Field(default=None, ge=0.0, le=14.0)

    # --- 凝集体 ---
    aggregate_diameter_um: float | None = Field(
        default=None, ge=0.0, description="Mean aggregate diameter [µm]"
    )
    large_aggregate_ratio: float = Field(
        0.0, ge=0.0, le=1.0, description="Fraction of aggregates >400 µm"
    )
    circularity: float | None = Field(default=None, ge=0.0, le=1.0)
    aspect_ratio: float | None = Field(default=None, ge=1.0)

    # --- 培養プロセス ---
    culture_age_d: float = Field(0.0, ge=0.0, description="Elapsed culture age [days]")
    phase: CulturePhase = Field("seed", description="Current culture phase")
    media_volume_ml: float = Field(150.0, gt=0.0, description="Working volume [mL]")

    # --- 前回 setpoint（ramp 制限判定用） ---
    last_perfusion_rate_vvd: float | None = Field(default=None)
    last_agitation_rpm: float | None = Field(default=None)
    last_do_setpoint_pct: float | None = Field(default=None)
    last_ph_setpoint: float | None = Field(default=None)
    last_setpoint_at: datetime | None = Field(default=None)

    # --- タイムスタンプ ---
    measured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # --- S02 反映: CSPR 作業範囲 ---
    @computed_field
    @property
    def cspr_pL_per_cell_per_day(self) -> float | None:
        """Cell-specific perfusion rate [pL/cell/day].

        CSPR = perfusion_rate_vvd / vcd * 1e12.
        7 vvd @ 35e6 cells/mL → 200 pL/cell/day.
        """
        if self.vcd <= 0.0:
            return None
        return self.perfusion_rate_vvd / self.vcd * 1e12

    @computed_field
    @property
    def cspr_status(self) -> Literal["low", "ok", "high"] | None:
        cspr = self.cspr_pL_per_cell_per_day
        if cspr is None:
            return None
        if cspr < 150.0:
            return "low"
        if cspr > 500.0:
            return "high"
        return "ok"

    @model_validator(mode="after")
    def _check_cspr_advisory(self) -> "CellCultureEnv":
        # 値は env では validation error にしない。events/sanitizer で取り扱う。
        return self


# --- CPP 包絡線（Limit / Warning / Trigger） ---
# 出典: kg_to_auto_cell.md §4 + S02 反映
class CppEnvelope:
    PH_LIMIT = (6.9, 7.3)
    PH_WARNING = (6.95, 7.25)

    DO_LIMIT = (5.0, 50.0)
    DO_WARNING = (8.0, 45.0)

    AGITATION_LIMIT = (30.0, 150.0)
    AGITATION_WARNING = (40.0, 140.0)

    PERFUSION_LIMIT = (0.0, 7.0)  # Manstein 2021 Table 3

    LACTATE_LIMIT = 50.0
    LACTATE_WARNING = 35.0

    GLUCOSE_LIMIT = 1.5
    GLUCOSE_WARNING = 1.8

    GLUTAMINE_LIMIT = 0.005
    GLUTAMINE_WARNING = 0.008

    OSMOLALITY_LIMIT = 500.0
    OSMOLALITY_WARNING = 450.0

    AGGREGATE_MEAN_LIMIT = (150.0, 400.0)  # <150 or >400
    AGGREGATE_MEAN_WARNING = (150.0, 350.0)

    LARGE_AGGREGATE_WARNING = 0.15
    LARGE_AGGREGATE_LIMIT = 0.20

    VCD_PASSAGE_TARGET = 35.0e6

    TEMP_LIMIT = (36.0, 38.0)
    TEMP_WARNING = (36.5, 37.5)


# --- S02 反映: 暫定 ramp 制限 ---
class RampLimits:
    """保守的な変化率制限。単位は「単位時間あたりの変化量」。"""

    PERFUSION_VVD_PER_HOUR = 0.25  # vvd/h
    AGITATION_RPM_PER_HOUR = 5.0   # rpm/h
    DO_PCT_PER_HOUR = 5.0          # %/h
    PH_PER_HOUR = 0.05             # pH/h
```

### 2.3 テスト例

```python
# tests/plugins/test_cell_culture_env.py
from auto_cell.plugins.cell_culture.environment import CellCultureEnv, CppEnvelope


def test_cspr_computation():
    env = CellCultureEnv(
        vcd=35e6,
        perfusion_rate_vvd=7.0,
        viability_pct=95.0,
        glucose_mM=5.0,
        lactate_mM=10.0,
        glutamine_mM=0.1,
        ph=7.1,
        do_pct=40.0,
        temp_c=37.0,
        osmolality_mOsm_kg=320.0,
        agitation_rpm=80.0,
    )
    assert env.cspr_pL_per_cell_per_day == 7.0 / 35e6 * 1e12
    assert env.cspr_status == "ok"
```

---

## 3. `channels.py` — `channel_config` / `route_channel`

### 3.1 設計方針

- `channel_config` は「MQTT/LADS 上のどのセンサをどの `CellCultureEnv` フィールドに書き込むか」を宣言する。
- `lads_function` 列は LADS Functional Unit 内の Function 名の例（協業 ICD で確定）。
- `route_channel` は topic または Function ID を受け取り、env 更新辞書を返す。対象外なら `None` を返す。

### 3.2 コード

```python
# src/auto_cell/plugins/cell_culture/channels.py
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChannelConfig(BaseModel):
    channel_id: str
    env_field: str
    lads_function: str | None = None
    unit: str
    kind: str = Field(..., pattern="^(analog|discrete|image|computed)$")
    cadence_s: float | None = None
    deadband: float | None = None


CHANNELS: list[ChannelConfig] = [
    ChannelConfig("vcd", "vcd", "BioProcessSensor_VCD", "cells/mL", "analog", 30.0),
    ChannelConfig("viability", "viability_pct", "BioProcessSensor_Viability", "%", "analog", 30.0),
    ChannelConfig("glucose", "glucose_mM", "BioProcessSensor_Glucose", "mM", "analog", 30.0),
    ChannelConfig("lactate", "lactate_mM", "BioProcessSensor_Lactate", "mM", "analog", 30.0),
    ChannelConfig("glutamine", "glutamine_mM", "BioProcessSensor_Glutamine", "mM", "analog", 30.0),
    ChannelConfig("ammonia", "ammonia_mM", "BioProcessSensor_Ammonia", "mM", "analog", 60.0),
    ChannelConfig("ph", "ph", "BioProcessSensor_pH", "pH", "analog", 5.0),
    ChannelConfig("do", "do_pct", "BioProcessSensor_DO", "%", "analog", 5.0),
    ChannelConfig("co2", "co2_pct", "BioProcessSensor_CO2", "%", "analog", 10.0),
    ChannelConfig("temp", "temp_c", "BioProcessSensor_Temperature", "°C", "analog", 5.0),
    ChannelConfig("osmolality", "osmolality_mOsm_kg", "BioProcessSensor_Osmolality", "mOsm/kg", "analog", 60.0),
    ChannelConfig("agitation", "agitation_rpm", "AgitationController_ActualSpeed", "rpm", "analog", 5.0),
    ChannelConfig("perfusion_rate", "perfusion_rate_vvd", "PerfusionController_ActualRate", "vvd", "analog", 5.0),
    ChannelConfig("aggregate_diameter", "aggregate_diameter_um", "AggregateAnalyzer_MeanDiameter", "µm", "analog", 300.0),
    ChannelConfig("large_aggregate_ratio", "large_aggregate_ratio", "AggregateAnalyzer_LargeFraction", "-", "analog", 300.0),
    ChannelConfig("sterility", "contamination_suspected", "SterilityMonitor_Contamination", "bool", "discrete", 0.0),
]


def channel_config() -> list[ChannelConfig]:
    return CHANNELS


def route_channel(channel_id: str, payload: Any) -> dict[str, Any] | None:
    """MQTT/LADS channel ID → CellCultureEnv 更新辞書。

    payload は数値または {'value': ..., 'timestamp': ...} の形式を受け入れる。
    """
    for ch in CHANNELS:
        if ch.channel_id == channel_id:
            value = payload["value"] if isinstance(payload, dict) and "value" in payload else payload
            return {ch.env_field: value}
    return None
```

### 3.3 テスト例

```python
def test_route_channel():
    update = route_channel("do", {"value": 41.2, "timestamp": "2026-06-30T07:00:00Z"})
    assert update == {"do_pct": 41.2}

    assert route_channel("unknown", 1.0) is None
```

---

## 4. `events.py` — イベント判定と抑制窓

### 4.1 設計方針

- 各イベントは P0–P3 の優先度、テキスト説明、抑制窓 [s] を持つ。
- `detect_events(env, now)` は `env` を閾値と比較し、アクティブなイベントを返す。
- 抑制は呼び出し側（L1 サイクル or HMI dispatcher）で「同じイベントが抑制窓内に再度発火しない」ように行う。
- `contamination_suspected` のみ抑制窓 0（即時）。
- S02 反映: `ammonia_high` は検出対象外（参考監視値）。

### 4.2 コード

```python
# src/auto_cell/plugins/cell_culture/events.py
from __future__ import annotations

from dataclasses import dataclass, field
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


def suppression_defaults() -> dict[str, int]:
    return {
    "ph_out_of_range": 300,
    "do_low": 300,
    "lactate_high": 600,
    "glucose_low": 300,
    "glutamine_low": 600,
    "osmolality_high": 600,
    "aggregate_out_of_range": 600,
    "large_aggregate_high": 600,
    "vcd_target_reached": 3600,
    "contamination_suspected": 0,
    "shear_risk": 300,
}


def _make(event_id: str, priority: Priority, field_name: str, now: datetime) -> CultureEvent:
    return CultureEvent(
        event_id=event_id,
        priority=priority,
        message=event_descriptions()[event_id],
        source_field=field_name,
        measured_at=now,
        suppression_window_s=suppression_defaults()[event_id],
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
```

### 4.3 テスト例

```python
def test_detect_do_low():
    env = _dummy_env()
    env.do_pct = 7.5
    events = detect_events(env)
    assert any(e.event_id == "do_low" for e in events)


def test_large_aggregate_high():
    env = _dummy_env()
    env.large_aggregate_ratio = 0.18
    events = detect_events(env)
    assert any(e.event_id == "large_aggregate_high" for e in events)
```

---

## 5. `tools.py` — 副作用ツールの schema と handler

### 5.1 設計方針

- `tool_schemas()` は OpenAI Function / JSON schema 形式の辞書を返す。
- `tool_handlers()` は名前→callable のマッピングを返す。
- handler は副作用の「意図」を表現する `ToolResult` を返す。実際の MQTT/LADS 送信は core の `tool_executor` が行う。
- `take_sample` は副作用が小さいが培養量を減らすため、副作用ツールとして扱う。

### 5.2 コード

```python
# src/auto_cell/plugins/cell_culture/tools.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
```

### 5.3 テスト例

```python
def test_invoke_set_perfusion_rate():
    result = invoke_tool("set_perfusion_rate", {"vvd": 3.5})
    assert result.status == "accepted"
    assert result.requested_actuators["perfusion_rate_vvd"] == 3.5
```

---

## 6. `sanitizer.py` — `validate_tool_call`

### 6.1 設計方針

- `validate_tool_call(env, tool_name, args)` は以下を検証する:
  1. **包絡線**: 各 setpoint/引数が `CppEnvelope` の Limit 内であること。
  2. **ramp 制限**: S02 暫定値に基づき、時間あたりの変化率が超過していないこと。
  3. **Y-27632 強制**: `trigger_passage` は `add_rock_inhibitor=True` を要求。
- 承認が必要な場合は `"approval_required"` を返し、 outright 拒否の場合は `"rejected"` を返す。
- 包絡線**外**の値は承認要求（安全側デフォルト）。包絡線内でも ramp 違反は拒否。

### 6.2 コード

```python
# src/auto_cell/plugins/cell_culture/sanitizer.py
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
```

### 6.3 テスト例

```python
def test_perfusion_ramp_limit_rejected():
    env = _dummy_env()
    env.perfusion_rate_vvd = 1.0
    env.last_perfusion_rate_vvd = 1.0
    env.last_setpoint_at = datetime.now(timezone.utc)  # 0 hours delta
    result, reason = validate_tool_call(env, "set_perfusion_rate", {"vvd": 2.0})
    assert result == "rejected"
    assert "ramp" in reason.lower()
```

---

## 7. `prompt.py` — L3 LLM 用システムプロンプトと状態要約

### 7.1 設計方針

- L3 は **非クリティカル用途限定**（Annex 22 対応）。プロンプトはバージョン管理する。
- `system_prompt_section()` は「絶対にやらないこと」を強調する。
- `build_culture_unit_summary(env, recent_events)` は LLM 入力用のテキストを生成。

### 7.2 コード

```python
# src/auto_cell/plugins/cell_culture/prompt.py
from __future__ import annotations

from datetime import datetime
from typing import Any

from auto_cell.plugins.cell_culture.environment import CellCultureEnv
from auto_cell.plugins.cell_culture.events import CultureEvent

PROMPT_VERSION = "2026-06-30-v1"


def system_prompt_section() -> str:
    return """\
You are an advisory assistant for an iPSC suspension/aggregate bioreactor controller (auto_cell A-layer).
You may ONLY suggest actions. All physical actuation is performed by a deterministic L1 rule engine and is gated by `validate_tool_call`.

CRITICAL CONSTRAINTS (never violate):
- Do NOT suggest setpoints outside validated CPP envelopes.
- Do NOT suggest rapid ramps; perfusion ≤0.25 vvd/h, agitation ≤5 rpm/h, DO ≤5%/h, pH ≤0.05/h.
- Any passage/dissociation MUST include ROCK inhibitor Y-27632.
- Contamination suspicion → immediate hold/notify operator; do NOT attempt to resume autonomously.
- You cannot override emergency stops, hard interlocks, or safety systems.

CURRENT PROTOCOL (Manstein 2021):
- Target VCD: 35×10⁶ cells/mL by day 7.
- Perfusion ramp: 0 → 7 vvd based on glucose/lactate/osmolality triggers.
- pH 7.1, DO 40% → 10%, agitation 50–120 rpm.
- Aggregate diameter target 150–350 µm; >400 µm fraction should remain <15%.

When you suggest an action, provide a concise rationale and the expected outcome.
"""


def build_culture_unit_summary(
    env: CellCultureEnv,
    recent_events: list[CultureEvent] | None = None,
    max_events: int = 5,
) -> str:
    recent_events = recent_events or []
    event_lines = "\n".join(
        f"- [{e.priority}] {e.event_id}: {e.message}"
        for e in recent_events[:max_events]
    ) or "- None"

    cspr = env.cspr_pL_per_cell_per_day
    cspr_str = f"{cspr:.1f}" if cspr is not None else "N/A"

    return f"""\
Culture unit summary (prompt version {PROMPT_VERSION}):
- Phase: {env.phase}, age: {env.culture_age_d:.2f} d
- VCD: {env.vcd:.2e} cells/mL, viability: {env.viability_pct:.1f}%
- Glucose: {env.glucose_mM:.2f} mM, Lactate: {env.lactate_mM:.2f} mM, Glutamine: {env.glutamine_mM:.3f} mM
- pH: {env.ph:.2f}, DO: {env.do_pct:.1f}%, Temp: {env.temp_c:.1f}°C, Osmolality: {env.osmolality_mOsm_kg:.1f} mOsm/kg
- Perfusion: {env.perfusion_rate_vvd:.2f} vvd, Agitation: {env.agitation_rpm:.1f} rpm
- Aggregate mean: {env.aggregate_diameter_um or 'N/A'} µm, large (>400 µm): {env.large_aggregate_ratio*100:.1f}%
- CSPR: {cspr_str} pL/cell/day (target 150–500)
- Ammonia (monitoring): {env.ammonia_mM if env.ammonia_mM is not None else 'N/A'} mM

Recent events:
{event_lines}
"""
```

---

## 8. `confidence.py` — 信頼度スコア層の骨格

### 8.1 設計方針

- モデルタイプ別に信頼度計算を分岐する。
- Phase 1 では **GP 事後分散**の骨格のみ実装。PLS/Raman、DL は stub。
- 低信頼度（<0.5）の場合は HITL エスカレーションを推奨。

### 8.2 コード

```python
# src/auto_cell/plugins/cell_culture/confidence.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ModelType = Literal["gp", "pls", "dl"]


@dataclass
class ConfidenceScore:
    score: float  # 0.0–1.0
    model_type: ModelType
    rationale: str
    escalate: bool


def confidence_from_gp_posterior(std: float, mean: float | None = None) -> ConfidenceScore:
    """Simple inverse-normalized uncertainty score."""
    # 仮: std が大きいほど信頼度が下がる。閾値は問題設定に応じて調整。
    scale = max(abs(mean), 1.0) if mean is not None else 1.0
    normalized = std / scale
    score = max(0.0, 1.0 - normalized)
    return ConfidenceScore(
        score=score,
        model_type="gp",
        rationale=f"GP posterior std={std:.3g} (normalized={normalized:.3g})",
        escalate=score < 0.5,
    )


def confidence_from_pls(x_residual: float, t2: float) -> ConfidenceScore:
    """Stub for PLS Q-residual / Hotelling T²."""
    score = 0.5  # placeholder
    return ConfidenceScore(
        score=score,
        model_type="pls",
        rationale=f"PLS Q-residual={x_residual:.3g}, T²={t2:.3g}",
        escalate=False,
    )


def confidence_from_dl(ensemble_std: float | None = None, mc_dropout_std: float | None = None) -> ConfidenceScore:
    """Stub for deep ensemble / MC dropout uncertainty."""
    score = 0.5
    return ConfidenceScore(
        score=score,
        model_type="dl",
        rationale="DL uncertainty stub",
        escalate=False,
    )


def compute_confidence(model_type: ModelType, **kwargs: Any) -> ConfidenceScore:
    if model_type == "gp":
        return confidence_from_gp_posterior(kwargs["std"], kwargs.get("mean"))
    if model_type == "pls":
        return confidence_from_pls(kwargs["q_residual"], kwargs["t2"])
    if model_type == "dl":
        return confidence_from_dl(kwargs.get("ensemble_std"), kwargs.get("mc_dropout_std"))
    raise ValueError(f"Unsupported model_type: {model_type}")
```

---

## 9. `aggregate_imaging.py` — Cellpose 統合と凝集体メトリクス

### 9.1 設計方針

- Cellpose 2.0/3.0 を第一に使用。import 失敗時は scikit-image ベースの簡易 watershed fallback を提供。
- 入力: 明視野/位相差 2D 画像（numpy array またはファイルパス）。
- 出力: mask, 個別凝集体径（等価円直径）、大径割合、円形度、アスペクト比。

### 9.2 コード

```python
# src/auto_cell/plugins/cell_culture/aggregate_imaging.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class AggregateMetrics:
    mean_diameter_um: float | None
    large_fraction: float  # >400 µm の面積割合
    circularity_mean: float | None
    aspect_ratio_mean: float | None
    count: int


def _load_image(image: np.ndarray | str | Path) -> np.ndarray:
    if isinstance(image, (str, Path)):
        from PIL import Image
        return np.array(Image.open(image).convert("L"))
    return np.asarray(image)


def _fallback_segment(image: np.ndarray) -> np.ndarray:
    """scikit-image based fallback if Cellpose is unavailable."""
    from skimage import filters, morphology, measure, segmentation
    blurred = filters.gaussian(image, sigma=2)
    thresh = filters.threshold_otsu(blurred)
    binary = blurred > thresh
    cleaned = morphology.remove_small_objects(binary, min_size=50)
    distance = morphology.distance_transform_edt(cleaned)
    local_max = morphology.local_maxima(distance)
    markers = measure.label(local_max)
    masks = segmentation.watershed(-distance, markers, mask=cleaned)
    return masks


def segment_aggregates(
    image: np.ndarray | str | Path,
    pixel_size_um: float,
    cellpose_model: str = "cyto",
    diameter_um: float | None = None,
    use_cellpose: bool = True,
) -> tuple[np.ndarray, AggregateMetrics]:
    """Segment aggregates and compute size/shape metrics.

    Args:
        image: 明視野または位相差画像（グレースケール推奨）。
        pixel_size_um: 1 pixel = ? µm。
        cellpose_model: "cyto" or "cyto2" etc.
        diameter_um: Cellpose 推定用の近似直径。
        use_cellpose: False の場合は scikit-image fallback。
    """
    img = _load_image(image)

    if use_cellpose:
        try:
            from cellpose import models
            model = models.Cellpose(model_type=cellpose_model)
            masks, _, _, _ = model.eval(
                img,
                diameter=diameter_um,
                channels=[0, 0],
                do_3D=False,
            )
        except Exception:
            masks = _fallback_segment(img)
    else:
        masks = _fallback_segment(img)

    from skimage import measure
    regions = measure.regionprops(masks)

    diameters = []
    circularities = []
    aspect_ratios = []
    large_area = 0
    total_area = 0
    for r in regions:
        area_px = r.area
        area_um2 = area_px * pixel_size_um**2
        eq_diameter_um = 2.0 * np.sqrt(area_um2 / np.pi)
        diameters.append(eq_diameter_um)
        if r.perimeter > 0:
            circularities.append(4.0 * np.pi * area_um2 / (r.perimeter * pixel_size_um) ** 2)
        if r.minor_axis_length > 0:
            aspect_ratios.append(r.major_axis_length / r.minor_axis_length)
        total_area += area_um2
        if eq_diameter_um > 400.0:
            large_area += area_um2

    count = len(diameters)
    metrics = AggregateMetrics(
        mean_diameter_um=float(np.mean(diameters)) if diameters else None,
        large_fraction=(large_area / total_area) if total_area > 0 else 0.0,
        circularity_mean=float(np.mean(circularities)) if circularities else None,
        aspect_ratio_mean=float(np.mean(aspect_ratios)) if aspect_ratios else None,
        count=count,
    )
    return masks, metrics
```

### 9.3 テスト例

```python
def test_aggregate_metrics_with_dummy_image():
    # 半径 50 px の円 → 等価径 100 px。pixel_size=2 µm/px → 200 µm。
    img = np.zeros((256, 256), dtype=np.uint8)
    rr, cc = disk((128, 128), 50)
    img[rr, cc] = 255
    masks, metrics = segment_aggregates(img, pixel_size_um=2.0, use_cellpose=False)
    assert metrics.count >= 1
    assert metrics.mean_diameter_um is not None
    assert 180.0 <= metrics.mean_diameter_um <= 220.0
```

---

## 10. テスト計画

| テストファイル | 対象 | 確認内容 |
|---|---|---|
| `tests/plugins/test_cell_culture_env.py` | `environment.py` | CSPR 計算、包絡線定数、Pydantic validation |
| `tests/plugins/test_cell_culture_channels.py` | `channels.py` | 全 channel の `route_channel` mapping、未知 channel は None |
| `tests/plugins/test_cell_culture_events.py` | `events.py` | 各イベントの閾値発火、優先度順序、抑制窓 |
| `tests/plugins/test_cell_culture_tools.py` | `tools.py` | schema 形状、handler 実行、actuator 辞書 |
| `tests/plugins/test_cell_culture_sanitizer.py` | `sanitizer.py` | 包絡線内 accepted、包絡線外 approval_required、ramp 違反 rejected、Y-27632 強制 |
| `tests/plugins/test_cell_culture_prompt.py` | `prompt.py` | プロンプトに制約文言が含まれる、summary が env 値を反映 |
| `tests/plugins/test_confidence_score.py` | `confidence.py` | GP score 計算、escalate 閾値 |
| `tests/plugins/test_aggregate_imaging.py` | `aggregate_imaging.py` | dummy 画像のセグメンテーション、メトリクス値の妥当性 |

### CI 統合方針

- `pytest tests/plugins/test_cell_culture_*` を Phase 1 CI に追加。
- Cellpose は重いため、画像テストは `use_cellpose=False` の fallback path を基本とする。
- GPU 依存テストは `pytest.mark.gpu` を付け、CI では skip する。

---

## 11. 依存関係

### 11.1 既存依存

- `pydantic`（core 経由または直接使用）
- `numpy`, `scipy`（`sim/plant_model` 用、plugin でも利用）

### 11.2 追加依存

| パッケージ | 用途 | 備考 |
|---|---|---|
| `cellpose>=2.0` | 凝集体セグメンテーション | GPU 不要で CPU 実行可。重いため optional-extra `imaging` に分離推奨 |
| `scikit-image` | Cellpose fallback、形態メトリクス | 軽量。required にしてよい |
| `Pillow` | 画像ファイル読み込み | scikit-image と同梱されることが多い |
| `torch` | Cellpose の backend | Cellpose インストール時に解決。明示しない場合も可 |

### 11.3 `pyproject.toml` 更新例

```toml
[project.optional-dependencies]
imaging = [
    "cellpose>=2.0",
    "scikit-image>=0.21",
]
```

`uv sync --extra dev --extra imaging` で開発環境を構築する。

---

## 12. リスクと対応

### 12.1 `physical-ai-core` の `DomainVertical` ABC 未確定

- **リスク**: core の ABC シグネチャが未確定のため、`CellCulturePlugin` の実装が後で差し替えになる。
- **対応**:
  1. `src/auto_cell/plugins/cell_culture/__init__.py` では仮 IF を定義する。
  2. core 確定後、`__init__.py` の継承先と slot メソッド名を機械的に差し替える。

```python
# src/auto_cell/plugins/cell_culture/__init__.py（仮 IF 例）
from __future__ import annotations

from auto_cell.plugins.cell_culture.environment import CellCultureEnv
from auto_cell.plugins.cell_culture.channels import channel_config, route_channel
from auto_cell.plugins.cell_culture.events import detect_events, event_descriptions, suppression_defaults
from auto_cell.plugins.cell_culture.tools import tool_schemas, tool_handlers
from auto_cell.plugins.cell_culture.sanitizer import validate_tool_call
from auto_cell.plugins.cell_culture.prompt import system_prompt_section, build_culture_unit_summary


try:
    from physical_ai_core import DomainVertical
except Exception:  # pragma: no cover
    class DomainVertical:
        domain_id: str = ""


class CellCulturePlugin(DomainVertical):
    domain_id = "cell_culture"
    display_name = "iPSC 浮遊/凝集体培養"

    def environment_model(self):
        return CellCultureEnv

    def channel_config(self):
        return channel_config()

    def route_channel(self, channel_id, payload):
        return route_channel(channel_id, payload)

    def detect_events(self, env, now=None):
        return detect_events(env, now)

    def event_descriptions(self):
        return event_descriptions

    def suppression_defaults(self):
        return suppression_defaults

    def tool_schemas(self):
        return tool_schemas()

    def tool_handlers(self):
        return tool_handlers()

    def validate_tool_call(self, env, tool_name, args):
        return validate_tool_call(env, tool_name, args)

    def system_prompt_section(self):
        return system_prompt_section()

    def build_culture_unit_summary(self, env, recent_events=None):
        return build_culture_unit_summary(env, recent_events)


plugin_class = CellCulturePlugin
```

### 12.2 その他リスク

| リスク | 対応 |
|---|---|
| Cellpose インストールが重い/失敗する | optional extra に分離し、fallback テストでカバー |
| S02 の ramp 値が実機では不適切 | 設定ファイル化し、校正時に上書き可能にする |
| LADS Function 名が協業 ICD で変更 | `channels.py` の `lads_function` 列を YAML 化し、ICD 確定時に差し替え |
| ammonia 閾値が後日確定 | `ammonia_mM` を env に保持し、`events.py` 側で 1 行追加でイベント化できる構造にする |

---

## 13. 実装工数見積もり（週単位）

`05_implementation_plan_phase1.md` Sprint 3–4, 8–9 に対応。

| 週 | タスク | 担当 | 完了基準 | 工数（想定） |
|---|---|---|---|---|
| Week 3 | `environment.py` + `channels.py` + テスト | 開発者 2 | `CellCultureEnv` 全フィールド、CSPR 計算、channel mapping | 1 週間 |
| Week 4 | `events.py` + `tools.py` + `sanitizer.py` + テスト | 開発者 2 | 全 11 イベント、7 ツール、ramp/Y-27632 検証 | 1 週間 |
| Week 8 | `prompt.py` + L3 統合準備（薄い実装） | 開発者 2/6 | システムプロンプト、状態要約、LLM 入出力ログ IF | 0.5 週間（並行） |
| Week 9 | `aggregate_imaging.py` + `confidence.py` + テスト | 開発者 2/6 | Cellpose/fallback セグメンテーション、メトリクス、信頼度骨格 | 1 週間 |
| Week 10 | 統合・リファクタ・ドキュメント | 開発者 2 | plugin 全テスト pass、E2E 閉ループ参加 | 0.5 週間 |
| **合計** | | | | **約 4 週間（並行含む実質 2.5 人週）** |

---

## 14. 次のステップ

1. 本計画をレビューし、S02 の暫定 ramp 値・CSPR 範囲に承認を得る。
2. `src/auto_cell/plugins/cell_culture/` にファイルを作成し、Week 3 から実装を開始する。
3. `physical-ai-core` の `DomainVertical` ABC 確定に伴い、`__init__.py` の仮 IF を正式 IF に差し替える。
4. `pyproject.toml` に `imaging` optional extra を追加する。

---

## 15. 参照

- `docs/design/closed_loop_planning/05_implementation_plan_phase1.md`
- `docs/design/closed_loop_planning/06_critical_path_and_work_order.md`
- `docs/design/closed_loop_planning/03_swarm_findings_integration.md`
- `docs/design/closed_loop_planning/02_missing_assets_for_closed_loop.md`
- `docs/design/kg_to_auto_cell.md`
- `src/auto_cell/plugins/cell_culture/__init__.py`
