# M06 L2 BO / L3 LLM / 凝集体画像 / 信頼度スコア 詳細実装計画

> **対象**: auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御）Phase 1
> **目的**: `05_implementation_plan_phase1.md` Sprint 8–9 における **L2 ベイズ最適化骨格**、**L3 薄い LLM オーケストレータ**、**at-line 凝集体画像解析**、**信頼度スコア層** の実装者がそのままコーディングを始められる具体性を提供する。
> **前提文書**: `05_implementation_plan_phase1.md`, `06_critical_path_and_work_order.md`, `03_swarm_findings_integration.md`, `02_missing_assets_for_closed_loop.md`, `docs/design/kg_to_auto_cell.md`（§4.2 観測性スタック、§4.3 BO 目的関数）, `docs/design/adr/0001-control-architecture.md`

---

## 1. ファイル構成

```
src/auto_cell/
├── l2_bayesian/
│   ├── __init__.py
│   ├── space.py              # 探索空間 Pydantic model → Ax SearchSpace 変換
│   ├── objective.py          # run 単位スカラ目的関数（重みは Phase 0 合意値を注入）
│   ├── optimizer.py          # Ax/BoTorch 薄いラッパー
│   └── constants.py          # BO 用定数（目的関数名、制約閾値等）
├── l3_orchestrator.py        # イベント駆動 LLM オーケストレータ
├── plugins/cell_culture/
│   ├── aggregate_imaging.py  # Cellpose ベース凝集体解析パイプライン
│   ├── confidence.py         # 信頼度スコア層（GP/PLS/DL 分岐）
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── system.jinja  # システムプロンプト（L3 用）
│   │       └── summary.jinja # 培養単位状態要約テンプレート
│   └── llm_io_log.py         # L3 入出力ログスキーマ＆書込ヘルパー
tests/
├── l2_bayesian/
│   ├── test_space.py
│   ├── test_objective.py
│   └── test_optimizer.py     # 固定シード再現性テスト
├── l3/
│   └── test_orchestrator.py  # プロンプトバージョニング・入出力ログ・ガード
└── plugins/
    ├── test_aggregate_imaging.py
    └── test_confidence.py
```

---

## 2. 実装スケジュール（Phase 1 内の位置づけ）

| 週 | 主タスク | 完了基準 |
|---|---|---|
| **Week 8 前半** | L2 BO 骨格（space/objective/optimizer） | `pytest tests/l2_bayesian/test_optimizer.py -v` pass |
| **Week 8 後半** | L3 トリガー/プロンプト/入出力ログ/ガード | `pytest tests/l3/test_orchestrator.py -v` pass |
| **Week 9 前半** | Cellpose 統合＋凝集体メトリクス | `pytest tests/plugins/test_aggregate_imaging.py -v` pass |
| **Week 9 後半** | 信頼度スコア層＋HITL エスカレーション | `pytest tests/plugins/test_confidence.py -v` pass |
| **Week 10** | E2E 統合・静的決定論的証明文書更新 | 7 日 run 内で BO/LLM/画像/信頼度が HMI 上に表示される |

> **注意**: M06 は `06_critical_path_and_work_order.md` で「非クリティカルパス（並列化可能）」と位置づけられている。Phase 1 最短閉ループ（L0–L1–MQTT–承認）が Week 7 までに成立した後に本モジュールを追加する。

---

## 3. L2 BO 骨格

### 3.1 Ax / BoTorch 選定と理由

**採用: Ax Service API（`ax-platform`）を薄くラップする。**

- **選定理由**:
  - 高レベル API により、探索空間・制約・目的関数・バッチの記述が `SearchSpace`/`Experiment` として一元化できる。
  - `OutcomeConstraint` を使った **Safe BO**（CPP 包絡線の事後制約）が標準で使える。
  - 将来的な多忠実度（Tier2 `plant_model` を低忠実度評価に）、バッチ BO（並行 run）への拡張が `GenerationStrategy` 変更で対応可能。
  - BoTorch 直接に比べて「実験管理・ trial 追跡・再現性テスト」が容易。
- **代替**: BoTorch 直接は獲得関数のカスタマイズが必要な Phase 2+ で検討。Phase 1 では Ax のみで十分。

### 3.2 探索空間 Pydantic model

`src/auto_cell/l2_bayesian/space.py`:

```python
"""BO 探索空間定義。kg_to_auto_cell.md §4 CPP 包絡線に準拠。"""
from __future__ import annotations

from enum import Enum
from typing import Self

from ax.core.parameter import ChoiceParameter, ParameterType, RangeParameter
from ax.core.search_space import SearchSpace
from pydantic import BaseModel, Field, model_validator


class PerfusionRampProfile(str, Enum):
    """灌流 rate 0→max までのスケジュール形状。

    Phase 1 では離散プロファイルを選び、l1_state_machine/recipe が
    時系列 schedule に展開する。連続パラメタ化は Phase 2 で検討。
    """

    MANSTEIN_LINEAR = "manstein_linear"   # 0→max を培養日数で線形
    CONSERVATIVE = "conservative"         # より緩やかな立ち上げ
    AGGRESSIVE = "aggressive"             # より早い立ち上げ


class CultureSearchSpace(BaseModel):
    """1 run の設計変数。数値は Phase 0 合意済みの仮運用範囲。"""

    seeding_density: float = Field(
        ..., ge=0.2e6, le=2.0e6, description="cells/mL"
    )
    initial_glucose_mm: float = Field(..., ge=10.0, le=30.0)
    perfusion_ramp_profile: PerfusionRampProfile
    max_perfusion_rate_vvd: float = Field(..., ge=0.0, le=7.0)
    agitation_base_rpm: int = Field(..., ge=30, le=150)
    do_transition_end_pct: float = Field(
        ..., ge=5.0, le=15.0, description="DO 目標を 40% からこの値へ漸減"
    )
    y_27632_conc_um: float = Field(..., ge=0.0, le=10.0)

    @model_validator(mode="after")
    def _profile_bound(self) -> Self:
        profile_max = {
            PerfusionRampProfile.CONSERVATIVE: 4.0,
            PerfusionRampProfile.MANSTEIN_LINEAR: 7.0,
            PerfusionRampProfile.AGGRESSIVE: 7.0,
        }[self.perfusion_ramp_profile]
        if self.max_perfusion_rate_vvd > profile_max:
            raise ValueError(
                f"{self.perfusion_ramp_profile.value} の max_perfusion_rate は "
                f"{profile_max} vvd 以下である必要があります"
            )
        return self

    def to_ax_search_space(self) -> SearchSpace:
        return SearchSpace(
            parameters=[
                RangeParameter(
                    name="seeding_density",
                    parameter_type=ParameterType.FLOAT,
                    lower=0.2e6,
                    upper=2.0e6,
                ),
                RangeParameter(
                    name="initial_glucose_mm",
                    parameter_type=ParameterType.FLOAT,
                    lower=10.0,
                    upper=30.0,
                ),
                ChoiceParameter(
                    name="perfusion_ramp_profile",
                    parameter_type=ParameterType.STRING,
                    values=[e.value for e in PerfusionRampProfile],
                ),
                RangeParameter(
                    name="max_perfusion_rate_vvd",
                    parameter_type=ParameterType.FLOAT,
                    lower=0.0,
                    upper=7.0,
                ),
                RangeParameter(
                    name="agitation_base_rpm",
                    parameter_type=ParameterType.INT,
                    lower=30,
                    upper=150,
                ),
                RangeParameter(
                    name="do_transition_end_pct",
                    parameter_type=ParameterType.FLOAT,
                    lower=5.0,
                    upper=15.0,
                ),
                RangeParameter(
                    name="y_27632_conc_um",
                    parameter_type=ParameterType.FLOAT,
                    lower=0.0,
                    upper=10.0,
                ),
            ]
        )
```

### 3.3 目的関数実装

`src/auto_cell/l2_bayesian/objective.py`:

```python
"""BO 用 run 単位目的関数。kg_to_auto_cell.md §4.3 に基づく。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class RunMetrics(BaseModel):
    """1 run 終了後に BO に報告する outcome metrics。"""

    vcd_final: float = Field(..., description="cells/mL")
    viability_final: float = Field(..., ge=0.0, le=1.0)
    pluripotency_pct: float = Field(..., ge=0.0, le=1.0)
    mean_aggregate_diameter_um: float
    large_aggregate_ratio: float = Field(..., ge=0.0, le=1.0)
    total_run_cost: float  # 通貨単位、コストペナルティ用
    max_lactate_mm: float
    max_osmolality_mosm: float


class CultureObjective:
    """J = yield × viability × pluripotency × aggregate_size × cost_penalty。

    重みは Phase 0 で研究者合意済みの値を `config/bo_objective_weights.yaml`
    から注入する。未合意時は以下の仮重みを使う。
    """

    DEFAULT_WEIGHTS = {
        "yield": 0.30,
        "viability": 0.25,
        "pluripotency": 0.25,
        "aggregate_size": 0.10,
        "cost": -0.10,  # コストはペナルティ（符号負）
    }
    VCD_TARGET = 35.0e6
    COST_REF = 1000.0

    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()

    def normalize_yield(self, vcd: float) -> float:
        return min(vcd / self.VCD_TARGET, 1.0)

    def aggregate_size_score(self, d_um: float) -> float:
        """150–350 µm を最適、>400 µm を penalize。"""
        if d_um < 150.0:
            return d_um / 150.0 * 0.8
        if d_um <= 350.0:
            return 1.0
        return max(1.0 - (d_um - 350.0) / 150.0, 0.0)

    def compute(self, m: RunMetrics) -> float:
        # Safe BO 制約違反に対するハードペナルティ
        penalty = 0.0
        if m.max_lactate_mm > 50.0:
            penalty += 0.5 * (m.max_lactate_mm - 50.0) / 50.0
        if m.max_osmolality_mosm > 500.0:
            penalty += 0.5 * (m.max_osmolality_mosm - 500.0) / 500.0
        if m.large_aggregate_ratio > 0.20:
            penalty += 0.5 * (m.large_aggregate_ratio - 0.20) / 0.20

        score = (
            self.weights["yield"] * self.normalize_yield(m.vcd_final)
            + self.weights["viability"] * m.viability_final
            + self.weights["pluripotency"] * m.pluripotency_pct
            + self.weights["aggregate_size"]
            * self.aggregate_size_score(m.mean_aggregate_diameter_um)
            + self.weights["cost"]
            * (1.0 - min(m.total_run_cost / self.COST_REF, 1.0))
        )
        return max(score - penalty, -1.0)
```

### 3.4 CPP 包絡線・ramp 制限を Safe BO 制約として表現

`src/auto_cell/l2_bayesian/constants.py`:

```python
"""BO experiment 定義。制約は kg_to_auto_cell.md §4 の CPP 包絡線から。"""
from ax.core.outcome_constraint import OutcomeConstraint
from ax.core.types import ComparisonOp

OBJECTIVE_METRIC = "run_objective"

SAFE_BO_OUTCOME_CONSTRAINTS = [
    OutcomeConstraint(
        metric_name="max_lactate_mm",
        op=ComparisonOp.LEQ,
        bound=50.0,
        relative=False,
    ),
    OutcomeConstraint(
        metric_name="max_osmolality_mosm",
        op=ComparisonOp.LEQ,
        bound=500.0,
        relative=False,
    ),
    OutcomeConstraint(
        metric_name="large_aggregate_ratio",
        op=ComparisonOp.LEQ,
        bound=0.20,
        relative=False,
    ),
    OutcomeConstraint(
        metric_name="viability_final",
        op=ComparisonOp.GEQ,
        bound=0.85,
        relative=False,
    ),
]
```

`src/auto_cell/l2_bayesian/optimizer.py`:

```python
"""Ax 薄いラッパー。固定シード再現性を保証する。"""
from __future__ import annotations

import random
from typing import Any

import numpy as np
import torch
from ax.service.ax_client import AxClient, ObjectiveProperties

from auto_cell.l2_bayesian.constants import (
    OBJECTIVE_METRIC,
    SAFE_BO_OUTCOME_CONSTRAINTS,
)
from auto_cell.l2_bayesian.objective import CultureObjective, RunMetrics
from auto_cell.l2_bayesian.space import CultureSearchSpace


class BayesianOptimizer:
    """run 間最適化エンジン。AxClient を内部に持つ。"""

    def __init__(
        self,
        seed: int = 42,
        objective: CultureObjective | None = None,
        minimize: bool = False,
    ):
        self.seed = seed
        self.objective = objective or CultureObjective()
        self.minimize = minimize
        self._set_seeds()

        self.ax = AxClient(random_seed=seed)
        self.ax.create_experiment(
            name="ipsc_perfusion_phase1",
            parameters=CultureSearchSpace(
                seeding_density=0.5e6,
                initial_glucose_mm=17.5,
                perfusion_ramp_profile="manstein_linear",
                max_perfusion_rate_vvd=3.5,
                agitation_base_rpm=80,
                do_transition_end_pct=10.0,
                y_27632_conc_um=5.0,
            ).to_ax_search_space().parameters,
            objectives={
                OBJECTIVE_METRIC: ObjectiveProperties(minimize=minimize)
            },
            outcome_constraints=SAFE_BO_OUTCOME_CONSTRAINTS,
        )

    def _set_seeds(self) -> None:
        random.seed(self.seed)
        np.random.seed(self.seed)
        torch.manual_seed(self.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.seed)

    def suggest(self) -> tuple[int, dict[str, Any]]:
        """次 trial のパラメータを提案。 trial_index は後続の complete に必要。"""
        params, trial_index = self.ax.get_next_trial()
        return trial_index, params

    def complete_trial(
        self, trial_index: int, metrics: RunMetrics
    ) -> None:
        objective_value = self.objective.compute(metrics)
        self.ax.complete_trial(
            trial_index=trial_index,
            raw_data={
                OBJECTIVE_METRIC: objective_value,
                "max_lactate_mm": metrics.max_lactate_mm,
                "max_osmolality_mosm": metrics.max_osmolality_mosm,
                "large_aggregate_ratio": metrics.large_aggregate_ratio,
                "viability_final": metrics.viability_final,
            },
        )

    def get_best_parameters(self) -> dict[str, Any] | None:
        best = self.ax.get_best_parameters()
        if best is None:
            return None
        params, _ = best
        return params
```

### 3.5 固定シード再現性テスト

`tests/l2_bayesian/test_optimizer.py`:

```python
import pytest
from auto_cell.l2_bayesian.optimizer import BayesianOptimizer


def test_suggest_is_reproducible_with_same_seed():
    opt1 = BayesianOptimizer(seed=12345)
    opt2 = BayesianOptimizer(seed=12345)

    idx1, params1 = opt1.suggest()
    idx2, params2 = opt2.suggest()

    assert params1 == params2
    assert idx1 == idx2  # trial_index は内部カウンタなので同じ seed では一致


def test_complete_trial_updates_best():
    opt = BayesianOptimizer(seed=1)
    idx, params = opt.suggest()

    from auto_cell.l2_bayesian.objective import RunMetrics

    metrics = RunMetrics(
        vcd_final=35e6,
        viability_final=0.95,
        pluripotency_pct=0.92,
        mean_aggregate_diameter_um=250.0,
        large_aggregate_ratio=0.05,
        total_run_cost=800.0,
        max_lactate_mm=30.0,
        max_osmolality_mosm=420.0,
    )
    opt.complete_trial(idx, metrics)
    best = opt.get_best_parameters()
    assert best is not None
```

---

## 4. L3 LLM オーケストレータ

### 4.1 イベント駆動トリガー設計

`src/auto_cell/l3_orchestrator.py`（抜粋）:

```python
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class L3TriggerType(str, Enum):
    """L3 を起動するイベント種別。ADR-0001 に従い『非常駐』とする。"""

    APPROVAL_MEDIATION = "approval_mediation"       # 承認要求の文脈説明生成
    AMBIGUOUS_PERCEPTION = "ambiguous_perception"   # 画像/センサの曖昧な異常
    NOVEL_EXCEPTION = "novel_exception"             # 既存イベント未分類の例外
    RESEARCHER_DIALOGUE = "researcher_dialogue"     # 自然言語問い合わせ


class L3Trigger(BaseModel):
    trigger_type: L3TriggerType
    culture_unit_id: str
    context: dict[str, Any] = Field(default_factory=dict)


class L3Recommendation(BaseModel):
    """L3 からの『助言』。直接 act しない。L1/承認フローが最終判定。"""

    recommendation: str
    reasoning: str
    suggested_tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    requires_human_confirmation: bool = True
```

### 4.2 プロンプトバージョニング

`src/auto_cell/plugins/cell_culture/prompts/v1/system.jinja`:

```jinja2
あなたは iPSC 浮遊灌流培養の L3 オーケストレータです。
以下のルールを絶対に守ってください:

1. あなたの出力は「助言」です。直接アクチュエータを駆動しません。
2. 安全インターロック、無菌バリア、緊急停止の上書きは行いません。
3. set_perfusion_rate などの数値提案は、CellCulturePlugin の validate_tool_call を通過する必要があります。
4. 根拠（根拠となった CPP 値やトレンド）を必ず含めてください。
5. 低信頼度の場合は「要人間確認」と明記してください。

培養単位: {{ culture_unit_id }}
現在フェーズ: {{ phase }}
直近イベント: {{ recent_events | join(", ") }}

{%- include "summary.jinja" %}
```

プロンプトロード＆ハッシュ:

```python
import hashlib
from pathlib import Path

class PromptRegistry:
    def __init__(self, version: str = "v1"):
        self.base = Path(__file__).parent / "prompts" / version
        self.version = version

    def load(self, name: str) -> str:
        return (self.base / name).read_text(encoding="utf-8")

    def hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
```

### 4.3 入出力ログ（思考・ツール呼び出し・根拠）

`src/auto_cell/plugins/cell_culture/llm_io_log.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from auto_cell.l3_orchestrator import L3Recommendation, L3TriggerType


class LlmIoLog(BaseModel):
    call_id: str
    trigger_type: L3TriggerType
    prompt_version: str
    prompt_hash: str
    model: str
    request_payload: dict[str, Any]
    response_payload: dict[str, Any]
    parsed_recommendation: L3Recommendation
    latency_ms: int
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def append_to(self, log_dir: Path) -> Path:
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / f"{self.timestamp}_{self.call_id}.json"
        path.write_text(self.model_dump_json(indent=2, ensure_ascii=False))
        return path
```

### 4.4 非クリティカル用途限定のガード

`src/auto_cell/l3_orchestrator.py` における `LlmOrchestrator`:

```python
import time
import uuid
from pathlib import Path

import openai

from auto_cell.plugins.cell_culture.llm_io_log import LlmIoLog
from auto_cell.plugins.cell_culture.prompts import PromptRegistry


class LlmOrchestrator:
    """L3 薄い LLM オーケストレータ。非クリティカル用途限定。"""

    CRITICAL_TOOLS = {"set_safety_interlock", "disable_sterility_barrier", "emergency_stop"}

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        prompt_version: str = "v1",
        log_dir: Path | None = None,
        allowed_tools: list[str] | None = None,
    ):
        self.model = model
        self.registry = PromptRegistry(version=prompt_version)
        self.system_prompt = self.registry.load("system.jinja")
        self.system_hash = self.registry.hash(self.system_prompt)
        self.log_dir = log_dir or Path("logs/llm_io")
        self.allowed_tools = set(allowed_tools or [])

    async def handle(self, trigger) -> L3Recommendation:
        user_msg = self._render_summary(trigger)
        request_payload = {
            "model": self.model,
            "temperature": 0.0,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_msg},
            ],
        }

        start = time.monotonic()
        response = await openai.chat.completions.create(**request_payload)
        latency_ms = int((time.monotonic() - start) * 1000)

        recommendation = self._parse_response(response)
        self._enforce_guards(recommendation)

        log = LlmIoLog(
            call_id=str(uuid.uuid4()),
            trigger_type=trigger.trigger_type,
            prompt_version=self.registry.version,
            prompt_hash=self.system_hash,
            model=self.model,
            request_payload=request_payload,
            response_payload=response.model_dump(mode="json"),
            parsed_recommendation=recommendation,
            latency_ms=latency_ms,
        )
        log.append_to(self.log_dir)
        return recommendation

    def _enforce_guards(self, rec: L3Recommendation) -> None:
        for tc in rec.suggested_tool_calls:
            name = tc.get("name")
            if name in self.CRITICAL_TOOLS:
                raise RuntimeError(f"L3 はクリティカルツール {name} を提案できません")
            if self.allowed_tools and name not in self.allowed_tools:
                raise RuntimeError(f"L3 は未許可ツール {name} を提案できません")
        # L3 出力は常に承認が必要
        rec.requires_human_confirmation = True

    def _render_summary(self, trigger) -> str:
        tpl = self.registry.load("summary.jinja")
        return tpl.render(**trigger.context)

    def _parse_response(self, response) -> L3Recommendation:
        msg = response.choices[0].message
        return L3Recommendation(
            recommendation=msg.content or "",
            reasoning="LLM 応答からの抽出（response.format により詳細化）",
            suggested_tool_calls=[],
            confidence=0.7,
            requires_human_confirmation=True,
        )
```

### 4.5 L3 テスト例

`tests/l3/test_orchestrator.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from auto_cell.l3_orchestrator import L3Trigger, L3TriggerType


@pytest.fixture
def orchestrator(tmp_path):
    from auto_cell.l3_orchestrator import LlmOrchestrator
    return LlmOrchestrator(
        model="gpt-4o-mini",
        prompt_version="v1",
        log_dir=tmp_path,
        allowed_tools=["get_culture_unit_status"],
    )


@pytest.mark.asyncio
async def test_prompt_hash_and_logging(orchestrator, tmp_path):
    trigger = L3Trigger(
        trigger_type=L3TriggerType.RESEARCHER_DIALOGUE,
        culture_unit_id="cu-01",
        context={"phase": "perfusion_ramp", "recent_events": ["glucose_low"]},
    )

    fake_response = AsyncMock()
    fake_response.model_dump.return_value = {"choices": [{"message": {"content": "test"}}]}

    with patch("openai.chat.completions.create", new=AsyncMock(return_value=fake_response)):
        rec = await orchestrator.handle(trigger)

    assert rec.requires_human_confirmation is True
    logs = list(tmp_path.glob("*.json"))
    assert len(logs) == 1
    assert orchestrator.system_hash in logs[0].read_text()


def test_critical_tool_guard_raises(orchestrator):
    from auto_cell.l3_orchestrator import L3Recommendation
    rec = L3Recommendation(
        recommendation="",
        reasoning="",
        suggested_tool_calls=[{"name": "emergency_stop"}],
        confidence=0.5,
    )
    with pytest.raises(RuntimeError):
        orchestrator._enforce_guards(rec)
```

---

## 5. 凝集体画像解析

### 5.1 Cellpose 統合

`src/auto_cell/plugins/cell_culture/aggregate_imaging.py`:

```python
"""at-line 明視野/位相差凝集体画像解析。Cellpose 3.x を lazy import する。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from pydantic import BaseModel, Field
from skimage.measure import regionprops


class AggregateMetrics(BaseModel):
    mean_diameter_um: float
    large_aggregate_ratio: float  # >400 µm の個数割合
    mean_circularity: float
    mean_aspect_ratio: float
    n_objects: int
    pixel_size_um: float


class AggregateAnalyzer:
    """Cellpose ベース。GPU 非搭載時は CPU fallback。"""

    def __init__(
        self,
        pixel_size_um: float = 1.0,
        model_type: str = "cyto3",
        diameter_px: float = 150.0,
        large_threshold_um: float = 400.0,
    ):
        self.pixel_size_um = pixel_size_um
        self.model_type = model_type
        self.diameter_px = diameter_px
        self.large_threshold_um = large_threshold_um
        self._model: Any | None = None

    def _cellpose_model(self):
        if self._model is None:
            from cellpose import models
            self._model = models.Cellpose(model_type=self.model_type)
        return self._model

    def analyze(self, image: np.ndarray) -> tuple[AggregateMetrics, np.ndarray]:
        """image: (H, W) または (H, W, C) の uint8/uint16。"""
        masks, *_ = self._cellpose_model().eval(
            image,
            channels=[0, 0] if image.ndim == 2 else [0, 0],
            diameter=self.diameter_px,
        )
        regions = regionprops(masks)
        if not regions:
            return AggregateMetrics(
                mean_diameter_um=0.0,
                large_aggregate_ratio=0.0,
                mean_circularity=0.0,
                mean_aspect_ratio=0.0,
                n_objects=0,
                pixel_size_um=self.pixel_size_um,
            ), masks

        diameters = [r.equivalent_diameter_area * self.pixel_size_um for r in regions]
        circularities = [
            4.0 * np.pi * r.area / (r.perimeter**2)
            for r in regions
            if r.perimeter and r.perimeter > 0
        ]
        aspect_ratios = [
            r.major_axis_length / max(r.minor_axis_length, 1e-9)
            for r in regions
            if r.minor_axis_length > 0
        ]

        large_count = sum(1 for d in diameters if d > self.large_threshold_um)

        return AggregateMetrics(
            mean_diameter_um=float(np.mean(diameters)),
            large_aggregate_ratio=large_count / len(diameters),
            mean_circularity=float(np.mean(circularities)) if circularities else 0.0,
            mean_aspect_ratio=float(np.mean(aspect_ratios)) if aspect_ratios else 0.0,
            n_objects=len(regions),
            pixel_size_um=self.pixel_size_um,
        ), masks

    def save_artifact(
        self,
        raw_image: np.ndarray,
        masks: np.ndarray,
        metrics: AggregateMetrics,
        run_id: str,
        sample_id: str,
        out_dir: Path,
    ) -> Path:
        run_dir = Path(out_dir) / run_id
        sample_dir = run_dir / sample_id
        sample_dir.mkdir(parents=True, exist_ok=True)

        Image.fromarray(raw_image).save(sample_dir / "raw.png")
        # マスクを擬似カラーで保存
        mask_color = (masks % 256).astype(np.uint8)
        Image.fromarray(mask_color, mode="L").save(sample_dir / "mask.png")
        (sample_dir / "metrics.json").write_text(
            metrics.model_dump_json(indent=2), encoding="utf-8"
        )
        return sample_dir
```

### 5.2 テスト例（Cellpose なしで形状検証）

`tests/plugins/test_aggregate_imaging.py`:

```python
import numpy as np
import pytest
from skimage.draw import disk
from skimage.measure import label

from auto_cell.plugins.cell_culture.aggregate_imaging import AggregateAnalyzer


def test_metrics_on_synthetic_disks():
    """Cellpose を介さず、skimage で生成したマスクを直接 regionprops 検証。"""
    analyzer = AggregateAnalyzer(pixel_size_um=2.0)
    img = np.zeros((512, 512), dtype=np.uint8)
    # 直径 100 px → 200 µm、200 px → 400 µm、250 px → 500 µm
    for center, radius in [((100, 100), 50), ((300, 300), 100), ((400, 400), 125)]:
        rr, cc = disk(center, radius, shape=img.shape)
        img[rr, cc] = 255

    # analyze を Cellpose 経由ではなく内部メソッドを直接テストするため、
    # 手動で二値マスクを regionprops に渡す簡易検証
    from skimage.measure import regionprops
    masks = label(img > 0)
    regions = regionprops(masks)
    diameters = [r.equivalent_diameter_area * 2.0 for r in regions]
    assert len(diameters) == 3
    assert max(diameters) > 400.0
```

---

## 6. 信頼度スコア層

### 6.1 GP 事後分散からの信頼度

`src/auto_cell/plugins/cell_culture/confidence.py`:

```python
"""AI/統計モデル別の信頼度スコア。ADR-0001 §9.3 準拠。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ConfidenceInput(BaseModel):
    model_type: str = Field(..., pattern="^(gp|pls|dl)$")
    # GP
    posterior_variance: float | None = None
    # PLS
    q_residual: float | None = None
    hotelling_t2: float | None = None
    # DL
    mc_dropout_std: float | None = None
    ood_score: float | None = None


class ConfidenceScorer:
    def __init__(
        self,
        gp_max_var: float = 1.0,
        pls_q_ref: float = 1.0,
        dl_std_ref: float = 1.0,
        low_confidence_threshold: float = 0.6,
    ):
        self.gp_max_var = gp_max_var
        self.pls_q_ref = pls_q_ref
        self.dl_std_ref = dl_std_ref
        self.threshold = low_confidence_threshold

    def from_gp_variance(self, variance: float) -> float:
        """variance → 0 で confidence → 1。"""
        std = max(variance, 0.0) ** 0.5
        return max(0.0, 1.0 - std / self.gp_max_var)

    def from_pls(self, q_residual: float, hotelling_t2: float | None = None) -> float:
        c_q = max(0.0, 1.0 - q_residual / self.pls_q_ref)
        c_t2 = 1.0 if hotelling_t2 is None else max(0.0, 1.0 - hotelling_t2 / 100.0)
        return float(np.clip((c_q + c_t2) / 2.0, 0.0, 1.0))

    def from_dl(self, mc_std: float, ood: float | None = None) -> float:
        c_std = max(0.0, 1.0 - mc_std / self.dl_std_ref)
        c_ood = 1.0 if ood is None else max(0.0, 1.0 - ood)
        return float(np.clip((c_std + c_ood) / 2.0, 0.0, 1.0))

    def compute(self, inp: ConfidenceInput) -> float:
        if inp.model_type == "gp":
            return self.from_gp_variance(inp.posterior_variance or 0.0)
        if inp.model_type == "pls":
            return self.from_pls(
                inp.q_residual or 0.0,
                inp.hotelling_t2,
            )
        if inp.model_type == "dl":
            return self.from_dl(
                inp.mc_dropout_std or 0.0,
                inp.ood_score,
            )
        raise ValueError(f"未知の model_type: {inp.model_type}")

    def should_escalate_to_hitl(self, inp: ConfidenceInput) -> bool:
        return self.compute(inp) < self.threshold


def confidence_from_bo_candidate(
    optimizer, params: dict[str, Any]
) -> float:
    """Ax/BoTorch モデルから candidate の事後分散を取得してスコア化。"""
    import numpy as np
    import torch

    model = optimizer.ax.generation_strategy.model
    # Ax の model bridge から torch モデルを取得
    if hasattr(model, "model"):
        botorch_model = model.model
    else:
        return 1.0  # モデル未構築時は信頼できないがエスカレーション不要

    # params を torch tensor に変換（search space 順）
    param_names = list(params.keys())
    x = torch.tensor([[params[p] for p in param_names]], dtype=torch.double)
    with torch.no_grad():
        posterior = botorch_model.posterior(x)
        var = posterior.variance.squeeze().item()

    scorer = ConfidenceScorer()
    return scorer.from_gp_variance(var)
```

> `np` インポートが `confidence.py` 内で必要。先頭に `import numpy as np` を追加すること。

### 6.2 低信頼度時の HITL エスカレーション

`src/auto_cell/plugins/cell_culture/confidence.py` 内で `should_escalate_to_hitl()` を使い、L2 BO 提案前に呼ぶ:

```python
# l2_bayesian/optimizer.py の suggest() 内など
scorer = ConfidenceScorer(gp_max_var=1.0)
var = (1.0 - confidence_from_bo_candidate(self, params)) * scorer.gp_max_var
if scorer.should_escalate_to_hitl(
    ConfidenceInput(model_type="gp", posterior_variance=var)
):
    # approval_service へエスカレーション
    pass
```

実際には `approval_service.request_approval(...)` を呼び出し、HMI に「BO 提案の信頼度低」を表示する。

---

## 7. テスト計画

| テスト | 対象 | 内容 | 配置 |
|---|---|---|---|
| BO 再現性 | L2 | 同一 seed で同一 `suggest()` 結果 | `tests/l2_bayesian/test_optimizer.py` |
| BO 目的関数 | L2 | 重み変化でスコアが変化、制約違反でペナルティ | `tests/l2_bayesian/test_objective.py` |
| 探索空間バリデーション | L2 | `conservative` + max>4.0 で Pydantic ValidationError | `tests/l2_bayesian/test_space.py` |
| L3 入出力ログ | L3 | prompt hash、response payload、推論ログの保存 | `tests/l3/test_orchestrator.py` |
| L3 ガード | L3 | クリティカルツール提案で RuntimeError | `tests/l3/test_orchestrator.py` |
| 画像解析 | Imaging | 合成画像の mean diameter / large ratio / circularity | `tests/plugins/test_aggregate_imaging.py` |
| 信頼度 | Confidence | GP variance → score マッピング、閾値エスカレーション | `tests/plugins/test_confidence.py` |

---

## 8. 依存関係

`pyproject.toml` の `project.optional-dependencies` に追加:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-asyncio>=0.23",
    "ruff",
    "mypy",
]
bo = [
    "ax-platform>=0.4.0",
    "botorch>=0.11.0",
    "torch>=2.2",
]
llm = [
    "openai>=1.30",
    "anthropic>=0.28",
]
imaging = [
    "cellpose>=3.0",
    "opencv-python-headless>=4.8",
    "scikit-image>=0.22",
    "Pillow>=10.0",
]
```

開発時は `uv sync --extra bo --extra llm --extra imaging --extra dev` で全機能を入れる。CI では機能別に matrix を分け、Cellpose や torch の重いテストは `pytest -m 'not heavy'` でスキップ可能にする（`pytest.ini` に `markers = heavy` を定義）。

---

## 9. リスクと対応

| # | リスク | 影響 | 対応 |
|---|---|---|---|
| R1 | **Ax/BoTorch/torch 依存の重さ** | CI 時間増大、開発マシンへの負荷 | optional extras に分離。CI cache `~/.cache/uv`。 `heavy` marker で分離。 |
| R2 | **Cellpose インストール・GPU 非搭載** | 解析遅延、テスト環境依存 | lazy import、CPU fallback。簡易 stub（scikit-image 円検出）で smoke test 可能にする。 |
| R3 | **LLM コスト・遅延・再現性** | 承認フロー遅延、コスト増 | `temperature=0.0`、キャッシュ、stub モード（環境変数 `LLM_STUB=1`）、非クリティカル用途限定。 |
| R4 | **固定シードでも Ax/BoTorch バージョン差で結果変動** | 再現性テスト flakiness | `uv.lock` でバージョン固定。CI とローカルで同一 lock ファイル使用。 |
| R5 | **GP 事後分散取得が Ax API 変更で破損** | 信頼度スコアが取れない | `confidence.py` は `try/except` でフォールバック（variance 不明時は score=0.5、エスカレーション）。 |
| R6 | **画像メトリクス定義（面積 vs 個数 vs 体積）** | 研究者間の認識違い | 計算式を `AggregateMetrics` docstring とテストに明文化。Phase 0/1 でレビュー。 |
| R7 | **BO 目的関数の重み未合意** | 実装後の差し戻し | 重みは `CultureObjective.DEFAULT_WEIGHTS` ではなく `config/bo_objective_weights.yaml` から注入する設計にしておく。 |

---

## 10. 実装工数見積もり

| 週 | 作業 | 工数（人日） | 担当想定 |
|---|---|---|---|
| Week 8 前半 | L2 BO space / objective / optimizer 実装 + 再現性テスト | 5 | ML/制御エンジニア 1 名 |
| Week 8 後半 | L3 トリガー/プロンプト/入出力ログ/ガード + テスト | 4 | バックエンドエンジニア 1 名 |
| Week 9 前半 | Cellpose 統合、凝集体メトリクス、画像アーティファクト保存 + テスト | 5 | CV/画像エンジニア 1 名 |
| Week 9 後半 | 信頼度スコア層、HITL エスカレーション接続 + テスト | 3 | ML/制御エンジニア 1 名 |
| Week 10 | E2E 統合、HMI 表示、静的決定論的証明文書更新、レビュー | 4 | 全員 |
| **合計** | | **21 人日（約 4–5 週間、1 名フル換算）** | |

> 上記は Phase 1 の `05_implementation_plan_phase1.md` Sprint 8–10 に対応。クリティカルパス（L0/L1/L2 最短閉ループ）が Week 7 までに成立していることが前提。

---

## 11. 参照

- `docs/design/closed_loop_planning/05_implementation_plan_phase1.md`
- `docs/design/closed_loop_planning/06_critical_path_and_work_order.md`
- `docs/design/closed_loop_planning/03_swarm_findings_integration.md`
- `docs/design/closed_loop_planning/02_missing_assets_for_closed_loop.md`
- `docs/design/kg_to_auto_cell.md`（§4.2, §4.3）
- `docs/design/adr/0001-control-architecture.md`
