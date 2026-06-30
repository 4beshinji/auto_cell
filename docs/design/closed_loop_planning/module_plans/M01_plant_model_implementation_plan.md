# M01 `sim/plant_model` 詳細実装計画

> **Scope**: auto_cell A 層 Tier2 plant_model — iPSC 浮遊/凝集体バイオリアクター
> **原典**: Manstein, Ullmann, Triebert & Zweigerdt 2021 (_Stem Cells Transl Med_ 10:1063-1080 / _STAR Protocols_ 2:100988, Table 1)
> **検証目標**: 7 日間で 0.5×10⁶ cells/mL → ~35×10⁶ cells/mL、DO 40→10 %、pH 7.1
> **前提文書**: `05_implementation_plan_phase1.md`, `06_critical_path_and_work_order.md`, `03_swarm_findings_integration.md`, `02_missing_assets_for_closed_loop.md`, `kg_to_auto_cell.md` §6

---

## 1. ファイル構成

```
sim/plant_model/
├── __init__.py              # パブリック API: PlantModel, PlantState, Actuators, Sensors, seed()
├── constants.py             # MansteinConstants dataclass + 単位変換
├── state.py                 # PlantState, Actuators, Sensors (Pydantic / dataclass)
├── manstein_ode.py          # ODE 右辺 + perfusion 項
├── solver.py                # scipy solve_ivp ラッパ、離散化、決定性制御
├── factory.py               # 初期状態ファクトリ
└── _compat.py               # numpy/scipy 型ヒントヘルパー

tests/
├── test_plant_model_basics.py   # 定数、状態、右辺、決定性の即値テスト
└── test_plant_model.py          # golden test: 7 日 35×10⁶ cells/mL 軌道
```

**理由**: `manstein_ode.py` を数式コアとして独立させ、`solver.py` で離散化と決定性を、`factory.py` で初期条件を分離。将来 COBRApy+GEM や商用 co-sim への backend 差替は `__init__.py` の `PlantModel` 実装クラスを差し替えるだけで済む。

---

## 2. クラス・関数設計

### 2.1 定数 (`constants.py`)

```python
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
    do_setpoint_initial: float = 40.0 # %
    do_setpoint_late: float = 10.0    # % (day 6-7 への移行目標)
    temp_setpoint_c: float = 37.0
```

### 2.2 状態・入出力ベクタ (`state.py`)

```python
from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True)
class PlantState:
    """ODE 状態ベクタ (連続)."""

    vcd: float              # viable cells / mL
    viability: float        # 0-100 %
    glucose: float          # mM
    lactate: float          # mM
    glutamine: float        # mM
    osmolality: float       # mOsm/kg
    aggregate_diameter: float  # µm

    def to_array(self) -> NDArray[np.float64]:
        ...

    @classmethod
    def from_array(cls, arr: NDArray[np.float64]) -> Self:
        ...


@dataclass(frozen=True)
class Actuators:
    """1 ステップ中に plant_model に適用されるアクチュエータ値."""

    perfusion_rate_vvd: float = 0.0   # vessel volumes / day (0-7)
    agitation_rpm: float = 80.0       # rpm
    do_setpoint: float = 40.0         # %
    ph_setpoint: float = 7.1          # -
    feed_glucose: float = 0.0         # mmol (bolus; 0 if continuous perfusion only)
    feed_glutamine: float = 0.0       # mmol (bolus)


@dataclass(frozen=True)
class Sensors:
    """`step()` が返すセンサ出力."""

    vcd: float
    viability: float
    glucose: float
    lactate: float
    glutamine: float
    osmolality: float
    aggregate_diameter_um: float
    do_percent: float
    ph: float
    temp_c: float
```

### 2.3 プラントモデル本体 (`__init__.py`)

```python
class PlantModel:
    """L1 サイクルから呼ばれる唯一の IF: step(actuators) -> sensors."""

    def __init__(
        self,
        constants: MansteinConstants | None = None,
        initial_state: PlantState | None = None,
        solver_method: str = "RK45",
        rtol: float = 1e-6,
        atol: float = 1e-9,
    ) -> None:
        ...

    @property
    def state(self) -> PlantState:
        ...

    @property
    def time(self) -> float:
        ...

    def step(self, actuators: Actuators, dt: float = 30.0) -> Sensors:
        """
        現在時刻から dt (seconds) だけ積分し、センサ値を返す.

        Args:
            actuators: ステップ内で一定とみなすアクチュエータ値.
            dt: 積分区間 [s]. L1 cadence は 30 s+ なので default 30 s.

        Returns:
            ステップ終了時点のセンサ値.
        """
        ...

    def reset(self, state: PlantState | None = None) -> None:
        ...
```

### 2.4 ODE 右辺 (`manstein_ode.py`)

```python
from scipy.integrate import solve_ivp


def manstein_rhs(
    t: float,
    y: NDArray[np.float64],
    actuators: Actuators,
    constants: MansteinConstants,
    feed_composition: FeedComposition,
) -> NDArray[np.float64]:
    """6 項 Monod ODE の右辺."""
    ...


def perfusion_dilution(
    perfusion_rate_vvd: float,
    state: PlantState,
    feed: FeedComposition,
) -> dict[str, float]:
    """灌流による代謝物希釈・栄養供給項."""
    ...
```

### 2.5 ソルバー (`solver.py`)

```python
def integrate_deterministic(
    rhs: Callable[[float, NDArray[np.float64]], NDArray[np.float64]],
    y0: NDArray[np.float64],
    t_span: tuple[float, float],
    method: str = "RK45",
    rtol: float = 1e-6,
    atol: float = 1e-9,
) -> NDArray[np.float64]:
    """
    決定的な ODE 積分.

    - scipy.solve_ivp を使う.
    -  dense_output は使わず終点値のみ返す.
    -  solver 内で乱数を使わない.
    """
    ...
```

### 2.6 初期状態ファクトリ (`factory.py`)

```python
def seed_state(
    seeding_density: float = 0.5e6,   # cells/mL
    viability: float = 97.0,          # %
    initial_glucose: float = 17.5,    # mM (E8 suspension medium)
    initial_glutamine: float = 2.0,   # mM
    initial_lactate: float = 0.0,     # mM
    initial_osmolality: float = 315.0, # mOsm/kg
    constants: MansteinConstants | None = None,
) -> PlantState:
    ...
```

---

## 3. ODE 右辺の具体形

> ⚠️ 原論文本文は Berkeley Madonna コード (_STAR Protocols_ Data S1) でモデルを公開しているが、本文には数式が掲載されていない。以下は Table 1 の定数と原論文の記述（Monod-variables, perfusion, aggregate density constancy）から導いた**現時点での最善の具体形**である。Data S1 を取得後、`manstein_ode.py` のみを差し替えて golden test と照合する。

### 3.1 変数定義

| 記号 | 単位 | 意味 |
|------|------|------|
| $X$ | cells/mL | viable cell density (VCD) |
| $v$ | % | viability |
| $G$ | mM | glucose |
| $L$ | mM | lactate |
| $Q$ | mM | glutamine |
| $O$ | mOsm/kg | osmolality |
| $d$ | µm | aggregate diameter |
| $D$ | 1/day | perfusion rate (vvd) |

### 3.2 比増殖速度

```
µ_eff = µ_max
        × G / (K_Glc + G)
        × K_Lac / (K_Lac + L)
        × Q / (K_Gln + Q)
        × K_Osm / (K_Osm + O)
        × K_Agg / (K_Agg + d)
        × D / (K_Perf + D)         # K_Perf = 0.5 vvd と仮定; Data S1 で校正
```

**根拠**: 各 Monod-variable は「制限/抑制が小さいとき 1、大きいとき 0 に近づく」無次元乗算。乳酸・浸透圧・凝集体径は抑制項（$K/(K+C)$）、glucose/glutamine/perfusionは制限項（$C/(K+C)$）。

### 3.3 各状態の右辺

#### 1) VCD

```
dX/dt = µ_eff × X
```

細胞は cell retention デバイスで槽内に留まるため、灌流による直接流出はない。

#### 2) Viability

```
dv/dt = 0        # Phase 1: 一定。必要なら乳酸/浸透圧しきい値で減少を追加
v = clip(v, 0, 100)
```

原論文では d7 でも viability は高い。Phase 1 では固定として、イベント閾値の検証に集中する。

#### 3) Glucose

```
consumption = q_Glc × X              # mmol/mL/day
inflow      = D × (G_feed - G)       # vvd × (mM - mM) = mM/day

dG/dt = inflow - consumption
```

$G_feed$ は `feed_composition.glucose` から取得。Phase 1 perfusion protocol:

- day 0-1: $D=0$ (no perfusion)
- day 1-4: $G_{feed}=17.5$ mM (E8 full feed I)
- day 4-7: $G_{feed}=42.5$ mM (E8 full feed II)

#### 4) Lactate

```
production = q_Lac × X               # mmol/mL/day
outflow    = -D × L                  # 灌流による希釈

dL/dt = production + outflow
```

#### 5) Glutamine

```
consumption = q_Gln × X
inflow      = D × (Q_feed - Q)
spontaneous = -k_deg × Q             # 化学分解 (k_deg ≈ 0.003 /day @ 37°C, pH 7.1)

dQ/dt = inflow - consumption + spontaneous
```

$Q_{feed}$ は day 1-4 で 4.5 mM、day 4-7 で 5.0 mM。

#### 6) Osmolality

```
# 栄養・代謝物変動とベース添加を簡易モデル化
base_addition_rate = max(0, k_base × (7.1 - pH_setpoint_impact))  # pH 制御は外部 PID 前提
dO/dt = D × (O_feed - O) + osm_per_lac × dL/dt + osm_per_glc × dG/dt + base_addition_rate
```

より単純化された実装案（推奨）:

```
# 乳酸・グルコース濃度変化とベース添加からの寄与を 1 つの合成項で近似
# osmolality ≈ 基礎培地 osmolality + 乳酸等価項 + グルコース等価項
osm_from_solutes = 1.0 × (G - G_0) + 1.0 × (L - L_0) + 1.0 × (Q - Q_0)
dO/dt = D × (O_feed - O) + k_osm_lac × dL/dt + base_rate
```

Phase 1 では、golden test と osmolality ピーク抑制の検証が主目的なので、Data S1 からパラメータを補正する。

#### 7) Aggregate diameter

原論文の重要な発見：凝集体密度（個数/mL）は播種後ほぼ一定。細胞数増加が径増加を生む。

```
# 凝集体個数密度 N_agg = aggf × X_0 / n_cells_per_seed_aggregate
# 体積 ∝ X / N_agg,  直径 ∝ (X / N_agg)^(1/3)
# 簡易化: d(d)/dt = aggg × µ_eff × d

d(d)/dt = aggg × µ_eff × d
```

あるいは、$d = d_0 × (X / X_0)^{aggg/3}$ と解析解を使う実装も可能。どちらでも golden test に合わせて調整。

### 3.4 Perfusion 項のまとめ

```python
# perfusion_rate_vvd = D [1/day]
# ステップ内で一定（ゼロ次ホールド）とみなす
D = actuators.perfusion_rate_vvd

dilution = {
    "glucose": D * (feed.glucose - state.glucose),
    "lactate": D * (0.0 - state.lactate),          # 流入培地に乳酸は含まれない
    "glutamine": D * (feed.glutamine - state.glutamine),
    "osmolality": D * (feed.osmolality - state.osmolality),
}
```

### 3.5 Python 実装スニペット

```python
def manstein_rhs(t, y, actuators, constants, feed):
    state = PlantState.from_array(y)
    X, v, G, L, Q, O, d = (
        state.vcd,
        state.viability,
        state.glucose,
        state.lactate,
        state.glutamine,
        state.osmolality,
        state.aggregate_diameter,
    )
    D = actuators.perfusion_rate_vvd

    # Monod terms
    mu_eff = (
        constants.mu_max
        * (G / (constants.k_glc + G))
        * (constants.k_lac / (constants.k_lac + L))
        * (Q / (constants.k_gln + Q))
        * (constants.k_osm / (constants.k_osm + O))
        * (constants.k_agg / (constants.k_agg + d))
        * (D / (0.5 + D))          # K_Perf placeholder; to be calibrated against Data S1
    )

    # Mass balance
    dXdt = mu_eff * X
    dvdt = 0.0
    dGdt = D * (feed.glucose - G) - constants.q_glc * X
    dLdt = constants.q_lac * X - D * L
    dQdt = D * (feed.glutamine - Q) - constants.q_gln * X - 0.003 * Q

    # Osmolality: simplified; replace after Data S1 review
    base_rate = 0.0 if actuators.ph_setpoint >= 7.0 else 5.0  # placeholder
    dOdt = D * (feed.osmolality - O) + 1.0 * dLdt + base_rate

    # Aggregate growth
    dddt = constants.agg_growth * mu_eff * d

    return np.array([dXdt, dvdt, dGdt, dLdt, dQdt, dOdt, dddt])
```

---

## 4. `step(actuators) -> sensors` IF

### 4.1 シグネチャ

```python
def step(self, actuators: Actuators, dt: float = 30.0) -> Sensors:
    ...
```

### 4.2 入力

| フィールド | 型 | 範囲例 | 意味 |
|------------|-----|--------|------|
| `perfusion_rate_vvd` | float | 0.0–7.0 | 灌流率 [vessel volumes/day] |
| `agitation_rpm` | float | 30–150 | 撹拌回転数 |
| `do_setpoint` | float | 5–50 | DO 設定点 [%] |
| `ph_setpoint` | float | 6.9–7.3 | pH 設定点 |
| `feed_glucose` | float | ≥0 | ボーラス glucose [mmol] |
| `feed_glutamine` | float | ≥0 | ボーラス glutamine [mmol] |

### 4.3 出力

| フィールド | 型 | 意味 |
|------------|-----|------|
| `vcd` | float | cells/mL |
| `viability` | float | % |
| `glucose` | float | mM |
| `lactate` | float | mM |
| `glutamine` | float | mM |
| `osmolality` | float | mOsm/kg |
| `aggregate_diameter_um` | float | µm |
| `do_percent` | float | % (actuators.do_setpoint を追従、遅れは無視) |
| `ph` | float | actuators.ph_setpoint を追従 |
| `temp_c` | float | 37.0 (固定) |

### 4.4 状態保持

```python
class PlantModel:
    def __init__(...):
        self._t: float = 0.0
        self._state: PlantState = initial_state or seed_state()

    def step(self, actuators, dt=30.0):
        t_start = self._t
        t_end = self._t + dt / 86400.0   # 内部時刻は day
        feed = select_feed(t_start)       # day 1-4 / 4-7 で feed 組成切替
        rhs = lambda t, y: manstein_rhs(t, y, actuators, self._const, feed)
        y_end = integrate_deterministic(rhs, self._state.to_array(), (t_start, t_end))
        self._state = PlantState.from_array(y_end)
        self._t = t_end
        return sensors_from_state(self._state, actuators)
```

### 4.5 離散化

- 内部時刻は **day**。
- `dt` は seconds; L1 cadenceは 30 s+。
- アクチュエータ値はステップ内で **ゼロ次ホールド**。
- `scipy.integrate.solve_ivp` の `t_span=(t, t+dt/86400)` で終点のみ取得。
- `dense_output=False` で決定性を高める。

---

## 5. 決定性保証

同一 actuators 系列 → 同一 sensors 軌道を保つための設計:

| # | 対策 | 実装 |
|---|------|------|
| 1 | 固定初期状態 | `seed_state()` の全デフォルトを固定。テスト時は明示的に指定。 |
| 2 | 乱数不使用 | `manstein_rhs`, `solver.py` 内で `np.random` や `random` を呼ばない。 |
| 3 | ソルバー固定 | `scipy.solve_ivp(method="RK45", rtol=1e-6, atol=1e-9)` を default とし、変更時はテストで再 golden 化する。 |
| 4 | 単一終点積分 | `dense_output=False`、イベント検出なし。 |
| 5 | アクチュエータはステップ内一定 | 中間の補間や extrapolation を行わない。 |
| 6 | 浮動小数点の非結合性対策 | テストでは `np.testing.assert_allclose(..., rtol=1e-9)`。決定性テストではビット同一を目指さず、許容誤差内の一致で判定。 |
| 7 | 固定シードのテスト | `pytest --randomly-seed=0` 等、プロジェクトの乱数固定策と整合。 |

---

## 6. 初期状態ファクトリ

```python
# factory.py

def seed_state(
    seeding_density: float = 0.5e6,
    viability: float = 97.0,
    initial_glucose: float = 17.5,
    initial_glutamine: float = 2.0,
    initial_lactate: float = 0.0,
    initial_osmolality: float = 315.0,
    initial_aggregate_diameter: float = 50.0,
    constants: MansteinConstants | None = None,
) -> PlantState:
    """
    Manstein 2021 の single-cell inoculation 条件.
    150 mL DASbox, E8 + RI, 37°C, day 0 は perfusion なし.
    """
    return PlantState(
        vcd=seeding_density,
        viability=viability,
        glucose=initial_glucose,
        lactate=initial_lactate,
        glutamine=initial_glutamine,
        osmolality=initial_osmolality,
        aggregate_diameter=initial_aggregate_diameter,
    )
```

**初期設定値の出典**:

| パラメータ | 値 | 根拠 |
|------------|-----|------|
| seeding density | 0.5×10⁶ cells/mL | Manstein 2021 Fig. 1 |
| viability | 97 % | 同 |
| initial glucose | 17.5 mM | E8 suspension medium (3.15 g/L) |
| initial glutamine | 2.0 mM | E8 + 2 mM L-Gln 追加なし基礎値 |
| initial osmolality | 315 mOsm/kg | E8 basis medium |
| initial aggregate diameter | 50 µm | single-cell inoculation 直後の小凝集体仮定 |

---

## 7. テスト計画

### 7.1 即値テスト (`tests/test_plant_model_basics.py`)

```python
import numpy as np
import pytest

from sim.plant_model import PlantModel, Actuators, seed_state, MansteinConstants


def test_constants_match_manstein_2021_table1():
    c = MansteinConstants()
    assert c.mu_max == pytest.approx(1.35)
    assert c.k_glc == pytest.approx(1.5)
    assert c.k_lac == pytest.approx(50.0)
    assert c.k_gln == pytest.approx(0.01)
    assert c.k_osm == pytest.approx(500.0)
    assert c.k_agg == pytest.approx(175.0)


def test_no_perfusion_batch_reaches_low_density():
    """灌流なしでは ~2.3e6 cells/mL 前後で頭打ち（Nogueira/Olmer 標準バッチ）."""
    plant = PlantModel(initial_state=seed_state())
    act = Actuators(perfusion_rate_vvd=0.0)
    for _ in range(7 * 24 * 12):  # 30 min step for 7 days
        plant.step(act, dt=1800.0)
    assert plant.state.vcd < 5.0e6


def test_determinism_same_actuator_sequence():
    plant1 = PlantModel(initial_state=seed_state())
    plant2 = PlantModel(initial_state=seed_state())
    act = Actuators(perfusion_rate_vvd=1.0)
    for _ in range(100):
        s1 = plant1.step(act, dt=60.0)
        s2 = plant2.step(act, dt=60.0)
    np.testing.assert_allclose(
        np.array(plant1.state.to_array()),
        np.array(plant2.state.to_array()),
        rtol=1e-9,
    )
```

### 7.2 Golden test: 7 日 35×10⁶ cells/mL (`tests/test_plant_model.py`)

```python
def manstein_perfusion_profile(t_day: float) -> Actuators:
    """
    Manstein 2021 Stg2M プロトコルの簡易版.
    day 0-1: D=0; day 1-5: D=1→2 vvd; day 5-7: D=2→7 vvd.
    """
    if t_day < 1.0:
        d = 0.0
    elif t_day < 5.0:
        d = 1.0 + (2.0 - 1.0) * (t_day - 1.0) / 4.0
    else:
        d = 2.0 + (7.0 - 2.0) * min(1.0, (t_day - 5.0) / 2.0)
    return Actuators(
        perfusion_rate_vvd=d,
        agitation_rpm=80.0,
        do_setpoint=40.0 if t_day < 6.0 else 10.0,
        ph_setpoint=7.1,
    )


def test_seven_day_manstein_trajectory():
    plant = PlantModel(initial_state=seed_state())
    dt = 300.0  # 5 min
    n_steps = int(7 * 24 * 3600 / dt)

    trajectory = []
    for i in range(n_steps):
        act = manstein_perfusion_profile(plant.time)
        sensors = plant.step(act, dt=dt)
        trajectory.append(sensors)

    final = trajectory[-1]
    assert final.vcd == pytest.approx(35.0e6, rel=0.15)
    assert 5.0 <= final.do_percent <= 50.0
    assert 6.9 <= final.ph <= 7.3
    assert final.glucose > 1.5
    assert final.lactate < 50.0
    assert final.osmolality < 500.0
    assert 150.0 <= final.aggregate_diameter_um <= 350.0
```

### 7.3 異常系テスト

```python
def test_negative_state_clipped():
    """ODE 積分中に負値が出たら 0 に clip する."""
    ...


def test_excessive_perfusion_does_not_cause_numerical_blowup():
    """D=20 vvd など極端な入力でも solver が発散しない."""
    plant = PlantModel(initial_state=seed_state())
    act = Actuators(perfusion_rate_vvd=20.0)
    for _ in range(10):
        plant.step(act, dt=60.0)
    assert np.isfinite(plant.state.vcd)


def test_zero_viability_does_not_produce_nan():
    state = seed_state(viability=0.0)
    plant = PlantModel(initial_state=state)
    s = plant.step(Actuators(), dt=60.0)
    assert np.isfinite(s.vcd)
```

### 7.4 CI 設定

```yaml
# .github/workflows/ci.yml 追加項目
- name: Run plant_model tests
  run: |
    uv run pytest tests/test_plant_model_basics.py tests/test_plant_model.py -v
```

---

## 8. 依存関係

### 8.1 ランタイム依存

| ライブラリ | 用途 | 既存 `pyproject.toml` |
|------------|------|------------------------|
| `numpy` | 状態ベクタ演算 | ✅ dependencies |
| `scipy` | `solve_ivp` | ✅ dependencies |
| `pydantic` | `CellCultureEnv` 等との型整合 | 追加検討（plugin 側で使用） |

### 8.2 開発依存

| ライブラリ | 用途 | 既存 `pyproject.toml` |
|------------|------|------------------------|
| `pytest` | 単体テスト | ✅ dev |
| `pytest-benchmark` | ソルバー性能回帰 | 追加推奨 |
| `ruff`, `mypy` | lint/型 | ✅ dev |

### 8.3 追加不要なもの

- `torch`, `jaxdiffeq`, `diffrax`: Phase 1 は決定的 scipy ソルバーで十分。
- `pint`: 単位は docstring と型名で管理。複雑な単位換算は現時点では不要。

---

## 9. リスクと対応

| # | リスク | 影響 | 対応 |
|---|--------|------|------|
| R1 | **ODE 式が原典 Data S1 と一致しない** | Golden test が失敗、L1 検証リグとして不十分 | `manstein_ode.py` を分離したモジュールに保ち、Data S1 取得後に右辺のみ差し替え。右辺の仮定を文書化。 |
| R2 | **Stiff ODE で RK45 が遅い/失敗** | 7 日シミュレーションが CI 時間内に終わらない | `solver_method` を `LSODA` または `BDF` に切替可能にする。`PlantModel.__init__` の引数に `solver_method` を持たせ、テストで計測。 |
| R3 | **Perfusion 項の K_Perf / feed 組成が未校正** | 35e6 軌道の再現精度が低い | feed 組成を `FeedComposition` dataclass で外部化。golden test の tolerance を最初は 15 % とし、Data S1 反映後に絞る。 |
| R4 | **数値誤差による決定性テストのフレーク** | CI が不安定 | ビット同一ではなく `rtol=1e-9` で比較。異なるプラットフォームでの誤差を許容。 |
| R5 | **状態変数の負値** | 物理的不整合、solver 発散 | `PlantState.from_array()` で負値を 0 に clip。右辺内でも `max(C, 0)` を使用。 |
| R6 | **凝集体モデルが実データと乖離** | `aggregate_out_of_range` イベントの信頼性低下 | `agg_growth` を調整可能にし、at-line 画像データが得次第校正。Phase 1 ではイベント閾値を緩めに設定。 |

---

## 10. 実装工数見積もり

| 週 | タスク | 担当 | 完了基準 | 出力 |
|----|--------|------|----------|------|
| **Week 1 前半** | 定数・状態・Actuators/Sensors 定義 | 開発者 | mypy/ruff pass、`test_plant_model_basics.py` 骨格 | `constants.py`, `state.py`, `factory.py` |
| **Week 1 後半** | ODE 右辺実装 + perfusion 項 + solver ラッパ | 開発者 | 単独で 1 日分の積分が実行可能 | `manstein_ode.py`, `solver.py` |
| **Week 1 末** | `step()` IF 統合 | 開発者 | `PlantModel.step()` が動作 | `__init__.py` |
| **Week 2 前半** | Golden test 作成・調整 | 開発者 | 7 日シミュレーションが目標範囲に入る | `tests/test_plant_model.py` |
| **Week 2 後半** | 決定性テスト・異常系テスト・CI 統合 | 開発者 | `pytest tests/test_plant_model*.py` pass | CI 設定更新 |
| **Week 2 末** | plant_model レビュー | チーム | 定数・軌道・IF が原典/設計と一致 | レビュー記録 |

**合計: 2 週間**（`05_implementation_plan_phase1.md` Sprint 1+2 と一致）。

---

## 11. 次のアクション

1. **本計画書レビュー**（特に §3 ODE 具体形の仮定）。
2. **_STAR Protocols_ Data S1 (Berkeley Madonna code)** の取得依頼または著者連絡。
3. `sim/plant_model/` ファイル群の実装開始。
4. Week 1 終了時点で `test_plant_model_basics.py` を CI に登録。

---

## 12. 参照

- Manstein et al. 2021, _Stem Cells Transl Med_ 10(7):1063-1080. DOI: 10.1002/sctm.20-0453
- Manstein et al. 2021, _STAR Protocols_ 2(4):100988. DOI: 10.1016/j.xpro.2021.100988
- `docs/design/closed_loop_planning/05_implementation_plan_phase1.md`
- `docs/design/closed_loop_planning/06_critical_path_and_work_order.md`
- `docs/design/closed_loop_planning/03_swarm_findings_integration.md`
- `docs/design/closed_loop_planning/02_missing_assets_for_closed_loop.md`
- `docs/design/kg_to_auto_cell.md`
- `sim/plant_model/__init__.py`
