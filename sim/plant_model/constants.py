"""Manstein 2021 STAR Protocols Table 1 constants."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MansteinConstants:
    """Manstein 2021 STAR Protocols Table 1 の培養動態定数."""

    mu_max: float = 1.35              # /day
    k_glc: float = 1.5                # mM
    k_lac: float = 50.0               # mM
    k_gln: float = 0.01               # mM
    k_osm: float = 500.0              # mOsm/kg
    k_agg: float = 175.0              # µm (直径; 原典 350/2)
    q_glc: float = 1.474e-8           # mmol/cell/day
    q_lac: float = 2.37e-8            # mmol/cell/day
    q_gln: float = 1.856e-9           # mmol/cell/day
    agg_formation: float = 0.95       # aggf [-] 初期凝集効率
    agg_growth: float = 0.25          # aggg [-] 凝集体成長係数
    feed_glc_i: float = 17.5          # mM (E8 full feed I, 3.15 g/L 換算)
    feed_glc_ii: float = 42.5         # mM (E8 full feed II, 7.65 g/L 換算)
    feed_gln: float = 4.5             # mM (full feed I)
    feed_gln_ii: float = 5.0          # mM (full feed II)
    feed_osm: float = 335.0           # mOsm/kg (E8 basis osmolality)
    working_volume_ml: float = 150.0

    # 局所 PID 側で維持される検証済設定値 (Phase 1 では plant_model は追従のみ)
    ph_setpoint: float = 7.1
    do_setpoint_initial: float = 40.0  # %
    do_setpoint_late: float = 10.0    # % (day 6-7 への移行目標)
    temp_setpoint_c: float = 37.0
