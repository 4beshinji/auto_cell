"""CellCultureEnv Pydantic model and CPP envelope constants."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, computed_field

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

    model_config = {"extra": "allow"}

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

        vcd is in cells/mL. 1 mL = 1e12 pL, therefore:
        CSPR [pL/cell/day] = perfusion_rate_vvd / vcd * 1e9.
        7 vvd @ 35e6 cells/mL → 200 pL/cell/day.
        """
        if self.vcd <= 0.0:
            return None
        return self.perfusion_rate_vvd / self.vcd * 1e9

    @computed_field
    @property
    def cspr_status(self) -> Literal["low", "ok", "high"] | None:
        cspr = self.cspr_pL_per_cell_per_day
        if cspr is None:
            return None
        # Thresholds are based on the cells/mL CSPR formula used above.
        # 7 vvd @ 35e6 cells/mL ~= 200 pL/cell/day.
        if cspr < 150.0:
            return "low"
        if cspr > 500.0:
            return "high"
        return "ok"


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
