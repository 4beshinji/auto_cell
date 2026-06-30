# M03: L1 決定的レシピ/ルールエンジン実装計画

> 対象: auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御）Phase 1  
> 目的: ADR-0001 に基づく L1 run 内監督制御コアを、実装者がそのままコーディングを始められる粒度で定義する  
> 前提: `05_implementation_plan_phase1.md`, `06_critical_path_and_work_order.md`, `03_swarm_findings_integration.md`, `02_missing_assets_for_closed_loop.md`, `kg_to_auto_cell.md` §7.2, `adr/0001-control-architecture.md`

---

## 1. スコープと位置づけ

L1 決定的レシピ/ルールエンジンは、ADR-0001 で定義された **L0（デバイス局所 PID）と L2（run 間 BO）の間**に位置する run 内監督制御層である。

- **入力**: `CellCultureEnv`（センサ・CPP・培養日数・phase）、`detect_events()` のイベント、承認状態、レシピ DSL
- **出力**: `sanitizer` を通過した副作用ツールコール群（`set_perfusion_rate`, `feed`, `exchange_media`, `trigger_passage` 等）
- **性質**: 決定的・再現可能・30 s+ 周期またはイベント駆動
- **非責務**: 画像 DL 推論、自然言語 HMI、run 間最適化（これらは L2/L3）

---

## 2. ファイル構成

`src/auto_cell/` 以下に以下のファイルを新規作成する。

| ファイル | 責務 |
|---|---|
| `src/auto_cell/l1/types.py` | L1 内で共用する Pydantic モデル（`L1State`, `ActionCandidate`, `Rule`, `Recipe` 等） |
| `src/auto_cell/l1/recipe_loader.py` | YAML/JSON レシピの読み込み、バリデーション、正規化 |
| `src/auto_cell/l1/state_machine.py` | `transitions` ベースの培養 phase 状態機械 |
| `src/auto_cell/l1/rule_engine.py` | センサ/イベントトリガからアクション候補を生成する決定論的ルールエンジン |
| `src/auto_cell/l1/event_dispatcher.py` | `detect_events()` 出力をアクション候補に変換、優先順位付け・競合解消 |
| `src/auto_cell/l1/action_planner.py` | ルール候補＋レシピ候補のマージ、依存関係解消、実行順序決定 |
| `src/auto_cell/l1/cycle_executor.py` | 30 s+ 周期またはイベント駆動で L1 サイクルを回す実行器 |
| `src/auto_cell/l1/recipe_engine.py` | 上記コンポーネントを統合するファサード。外部（core/WorldModel）から呼ばれる主入口 |
| `src/auto_cell/l1/__init__.py` | 公開 API エクスポート |
| `src/auto_cell/l1/mqtt_bridge.py` | MQTT topic 契約に従った cmd/ack/state/approval/notify の送受信（gateway 層） |
| `config/recipes/manstein_phase1.yaml` | Phase 1 標準レシピ（Manstein プロトコル DSL 化） |
| `config/recipes/manstein_rules.yaml` | Phase 1 標準ルールセット |
| `tests/l1/test_l1_recipe_loader.py` | DSL 読み込み・バリデーションテスト |
| `tests/l1/test_l1_state_machine.py` | 状態遷移テスト |
| `tests/l1/test_l1_rule_engine.py` | ルール発火テスト |
| `tests/l1/test_l1_event_dispatcher.py` | イベント→アクション変換・競合解消テスト |
| `tests/l1/test_l1_cycle_executor.py` | サイクル実行器テスト（同期・非同期・承認統合） |
| `tests/l1/test_l1_recipe_engine.py` | レシピエンジン統合テスト |

> 配置方針: `l1/` をサブパッケージにして、将来 MPC/L2 拡張時に `l2_bayesian/` 等と並列にする。

---

## 3. レシピ DSL 設計

### 3.1 文法概要（YAML）

```yaml
recipe:
  id: manstein_phase1
  version: "0.1.0"
  title: "Manstein 2021 iPSC perfusion protocol"
  culture_unit_id: "cu_001"

  initial_state: seed

  setpoints:
    ph: { value: 7.1, unit: "pH" }
    do: { value: 40, unit: "%", transition_to: 10, transition_at_hours: 72 }
    temp: { value: 37, unit: "degC" }
    agitation_base: { value: 80, unit: "rpm" }

  variables:
    seed_density: { value: 0.5e6, unit: "cells/mL" }
    target_vcd: { value: 35e6, unit: "cells/mL" }
    max_perfusion: { value: 7.0, unit: "vvd" }
    perfusion_ramp_hours: { value: 120, unit: "h" }

  states:
    seed:
      entry_actions:
        - tool: set_gas_setpoint
          args: { parameter: "ph", value_ref: "setpoints.ph.value" }
        - tool: set_gas_setpoint
          args: { parameter: "do", value_ref: "setpoints.do.value" }
        - tool: set_agitation_rpm
          args: { rpm_ref: "setpoints.agitation_base.value" }
      exit_condition:
        and:
          - elapsed_hours: { ge: 0.5 }
          - sensor: vcd
            ge: { value_ref: "variables.seed_density.value" }
      on_exit:
        - tool: log
          args: { message: "seed phase completed" }

    perfusion_ramp:
      entry_actions:
        - tool: set_perfusion_rate
          args:
            rate: 0.0
            unit: "vvd"
      scheduled_actions:
        - every_hours: 1.0
          action:
            tool: ramp_perfusion
            args:
              target_ref: "variables.max_perfusion.value"
              duration_hours_ref: "variables.perfusion_ramp_hours.value"
      transitions:
        - target: passage_ready
          condition:
            sensor: vcd
            ge: { value_ref: "variables.target_vcd.value" }
          timeout_hours: 168
          on_timeout: hold

    passage_ready:
      entry_actions:
        - tool: notify
          args: { priority: "P1", message: "Passage criteria met; approval required" }
      transitions:
        - target: approved_passage
          condition:
            approval: trigger_passage
            state: approved
        - target: hold
          condition:
            approval: trigger_passage
            state: rejected
      timeout_minutes: 30
      on_timeout: hold

    approved_passage:
      entry_actions:
        - tool: trigger_passage
          args: { method: dissociate, add_rock_inhibitor: true }
      transitions:
        - target: reseed
          condition:
            event: passage_completed
        - target: hold
          condition:
            event: passage_failed

    reseed:
      entry_actions:
        - tool: set_perfusion_rate
          args: { rate: 0.0 }
      transitions:
        - target: seed
          condition:
            event: reseed_completed

    hold:
      entry_actions:
        - tool: set_perfusion_rate
          args: { rate: 0.0 }
        - tool: notify
          args: { priority: "P0", message: "Entering hold state" }
      transitions: []
```

### 3.2 DSL スキーマ（Pydantic）

```python
# src/auto_cell/l1/types.py
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class ScalarValue(BaseModel):
    value: float | int | str | bool
    unit: str | None = None


class ValueRef(BaseModel):
    ref: str  # "variables.max_perfusion.value", "setpoints.do.value"


class SensorCondition(BaseModel):
    sensor: str
    op: Literal["eq", "ne", "gt", "ge", "lt", "le", "in_range"]
    value: float | int | ValueRef | None = None
    min_value: float | int | ValueRef | None = None
    max_value: float | int | ValueRef | None = None
    for_minutes: float = 0.0  # 持続時間条件


class EventCondition(BaseModel):
    event: str
    op: Literal["occurred", "not_occurred", "suppressed"] = "occurred"
    within_minutes: float | None = None


class ApprovalCondition(BaseModel):
    approval: str
    state: Literal["approved", "rejected", "pending", "timeout"]


class LogicalCondition(BaseModel):
    and_: list[Condition] | None = Field(None, alias="and")
    or_: list[Condition] | None = Field(None, alias="or")
    not_: Condition | None = Field(None, alias="not")


Condition = SensorCondition | EventCondition | ApprovalCondition | LogicalCondition


class ToolCall(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


class ScheduledAction(BaseModel):
    every_hours: float | None = None
    every_minutes: float | None = None
    at_hours: list[float] | None = None
    action: ToolCall


class Transition(BaseModel):
    target: str
    condition: Condition | None = None
    timeout_hours: float | None = None
    timeout_minutes: float | None = None
    on_timeout: str | None = None  # 遷移先 state id


class State(BaseModel):
    id: str
    entry_actions: list[ToolCall] = Field(default_factory=list)
    scheduled_actions: list[ScheduledAction] = Field(default_factory=list)
    exit_condition: Condition | None = None
    transitions: list[Transition] = Field(default_factory=list)
    timeout_hours: float | None = None
    timeout_minutes: float | None = None
    on_timeout: str | None = None
    on_exit: list[ToolCall] = Field(default_factory=list)


class Recipe(BaseModel):
    id: str
    version: str
    title: str
    culture_unit_id: str
    initial_state: str
    setpoints: dict[str, ScalarValue] = Field(default_factory=dict)
    variables: dict[str, ScalarValue] = Field(default_factory=dict)
    states: dict[str, State]

    def get_state(self, state_id: str) -> State:
        if state_id not in self.states:
            raise KeyError(f"state {state_id!r} not in recipe")
        return self.states[state_id]
```

### 3.3 値参照解決

`value_ref` はドット区切りで DSL 内の値を参照する。解決時は以下の順序で探索する。

1. `variables.<id>.value`
2. `setpoints.<id>.value`
3. 特殊変数: `cycle.env.<field>`, `cycle.elapsed_hours`, `cycle.state_id`

```python
# src/auto_cell/l1/recipe_loader.py
class Context(BaseModel):
    recipe: Recipe
    env: "CellCultureEnv"
    elapsed_hours: float
    state_id: str
    event_log: list[str]
    approvals: dict[str, str]

    def resolve(self, ref: str) -> Any:
        if ref.startswith("variables."):
            key = ref.split(".")[1]
            return self.recipe.variables[key].value
        if ref.startswith("setpoints."):
            key = ref.split(".")[1]
            return self.recipe.setpoints[key].value
        if ref.startswith("cycle.env."):
            key = ref.split(".")[2]
            return getattr(self.env, key)
        if ref == "cycle.elapsed_hours":
            return self.elapsed_hours
        if ref == "cycle.state_id":
            return self.state_id
        raise ValueError(f"unresolvable ref: {ref}")
```

---

## 4. 状態機械

### 4.1 ライブラリ

`transitions`（Python 軽量 state machine ライブラリ）を採用する。

### 4.2 実装方針

`transitions.Machine` をラップし、Pydantic `Recipe` を状態定義ソースとする。条件判定は DSL の `Condition` を再帰的に評価する `ConditionEvaluator` で行う。アクションは「entry/exit/timeout」で `ToolCall` を生成するだけに留め、実際の実行はサイクル実行器が行う（状態機械は副作用を持たない）。

```python
# src/auto_cell/l1/state_machine.py
from __future__ import annotations

from transitions import Machine
from auto_cell.l1.types import Recipe, State, Condition, Context, ToolCall
from auto_cell.l1.recipe_loader import ConditionEvaluator


class RecipeStateMachine:
    def __init__(self, recipe: Recipe, context: Context):
        self.recipe = recipe
        self.context = context
        self.evaluator = ConditionEvaluator(context)
        self.pending_entry_actions: list[ToolCall] = []
        self.pending_exit_actions: list[ToolCall] = []

        states = list(recipe.states.keys())
        self.machine = Machine(
            model=self,
            states=states,
            initial=recipe.initial_state,
            send_event=True,
            auto_transitions=False,
        )

        for state_id, state in recipe.states.items():
            # entry/exit hooks
            self.machine.states[state_id].on_enter.append("_on_enter_state")
            self.machine.states[state_id].on_exit.append("_on_exit_state")

            for tx in state.transitions:
                trigger_name = f"to_{tx.target}"
                self.machine.add_transition(
                    trigger=trigger_name,
                    source=state_id,
                    dest=tx.target,
                    conditions=[self._make_condition(tx.condition)],
                    before=["_collect_exit_actions"],
                    after=["_collect_entry_actions"],
                )

    def _make_condition(self, condition: Condition | None):
        def predicate(event):
            if condition is None:
                return True
            self.context = self.context.model_copy(update={"elapsed_hours": event.kwargs.get("elapsed_hours", 0.0)})
            return self.evaluator.evaluate(condition)
        return predicate

    def _on_enter_state(self, event):
        state = self.recipe.get_state(self.state)
        self.pending_entry_actions.extend(state.entry_actions)

    def _on_exit_state(self, event):
        state = self.recipe.get_state(self.state)
        self.pending_exit_actions.extend(state.on_exit)

    def _collect_exit_actions(self, event):
        pass

    def _collect_entry_actions(self, event):
        pass

    def evaluate_transitions(self, elapsed_hours: float) -> list[str]:
        """現在 state から遷移可能な target state id を返す（副作用なし）。"""
        candidates = []
        state = self.recipe.get_state(self.state)
        for tx in state.transitions:
            trigger = getattr(self, f"to_{tx.target}")
            if trigger(elapsed_hours=elapsed_hours, skip=True):
                candidates.append(tx.target)
        return candidates

    def apply_timeout(self, elapsed_hours: float) -> str | None:
        state = self.recipe.get_state(self.state)
        timeout_h = state.timeout_hours
        if timeout_h is not None and elapsed_hours >= timeout_h:
            return state.on_timeout
        return None
```

> `transitions` の条件関数は `event` 引数を受け取る。`skip=True` は遷移を実際に実行せず判定だけ行うための工夫（要 `transitions` の `may` 相当）。実装時は `Machine.can_trigger` またはカスタムラッパで整理する。

### 4.3 状態遷移図

```
                    ┌─────────┐
         ┌─────────│  seed   │◄────────┐
         │         └────┬────┘         │
         │              │ exit_condition
         │              ▼                │
         │         ┌─────────────┐       │
         │         │perfusion_ramp│       │
         │         └──────┬──────┘       │
         │                │ vcd>=target  │
         │                ▼              │
         │          ┌─────────────┐      │
         │          │passage_ready│      │
         │          └──────┬──────┘      │
         │                 │ approval    │
         │    ┌────────────┼────────────┐│
         │    │            │            ││
         │reseed_completed│ approved   │rejected/timeout
         │    │            ▼            ││
         │    │    ┌───────────────┐   ││
         │    │    │approved_passage│   ││
         │    │    └───────┬───────┘   ││
         │    │            │ passage_completed
         │    │            ▼            ││
         │    │        ┌────────┐       ││
         └────┴────────│ reseed │───────┘│
                      └────┬───┘        │
                           │ any fault / timeout
                           ▼            │
                        ┌──────┐        │
                        │ hold │────────┘
                        └──────┘
```

---

## 5. ルールエンジン

### 5.1 設計方針

ルールは「IF センサ/イベント条件 THEN アクション候補（+優先度）」の決定論的リスト。ルールエンジンは各サイクルで `CellCultureEnv` とイベントを受け取り、発火したルールのアクション候補を返す。アクションは `ToolCall` 形式。優先度は P0（緊急）〜P3（情報）。

### 5.2 ルール DSL（YAML）

```yaml
rules:
  - id: emergency_do_low
    priority: P0
    when:
      event: do_low
    actions:
      - tool: set_agitation_rpm
        args: { rpm: 90 }
      - tool: notify
        args: { priority: P0, message: "DO low detected" }

  - id: emergency_contamination
    priority: P0
    when:
      event: contamination_suspected
    actions:
      - tool: set_perfusion_rate
        args: { rate: 0.0 }
      - tool: notify
        args: { priority: P0, message: "Contamination suspected; holding" }

  - id: glucose_low_feed
    priority: P2
    when:
      sensor: glucose
      le: 1.8
      for_minutes: 5.0
    actions:
      - tool: feed
        args:
          substance: glucose
          concentration_mM: 200.0
          target_bump_mM: 2.0

  - id: lactate_high_exchange
    priority: P1
    when:
      sensor: lactate
      ge: 35.0
      for_minutes: 10.0
    actions:
      - tool: exchange_media
        args:
          volume_ratio: 0.5

  - id: osmolality_high_increase_perfusion
    priority: P1
    when:
      sensor: osmolality
      ge: 450.0
    actions:
      - tool: set_perfusion_rate
        args:
          rate_ref: "variables.max_perfusion.value"

  - id: large_aggregate_high
    priority: P1
    when:
      event: large_aggregate_high
    actions:
      - tool: set_agitation_rpm
        args:
          rpm_ref: "setpoints.agitation_base.value"
          delta: 10
      - tool: notify
        args: { priority: P1, message: "Large aggregate ratio high" }
```

### 5.3 ルールエンジン実装

```python
# src/auto_cell/l1/rule_engine.py
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field
from auto_cell.l1.types import ToolCall, SensorCondition, EventCondition, Condition, LogicalCondition
from auto_cell.l1.recipe_loader import ConditionEvaluator
from auto_cell.plugins.cell_culture.environment import CellCultureEnv

Priority = Literal["P0", "P1", "P2", "P3"]


class Rule(BaseModel):
    id: str
    priority: Priority
    when: Condition
    actions: list[ToolCall]
    cooldown_minutes: float = 0.0  # 同じ rule id が再発火するまでの抑制時間


class RuleEngine:
    def __init__(self, rules: list[Rule]):
        self.rules = rules
        self.last_fired_at: dict[str, float] = {}  # rule_id -> elapsed_hours

    def evaluate(
        self,
        env: CellCultureEnv,
        events: list[str],
        elapsed_hours: float,
        approvals: dict[str, str] | None = None,
    ) -> list[ActionCandidate]:
        candidates: list[ActionCandidate] = []
        context = Context(
            recipe=None,  # ルールはレシピ変数を参照しない; 必要ならレシピを渡す
            env=env,
            elapsed_hours=elapsed_hours,
            state_id="",
            event_log=events,
            approvals=approvals or {},
        )
        evaluator = ConditionEvaluator(context)

        for rule in self.rules:
            last = self.last_fired_at.get(rule.id)
            if last is not None and (elapsed_hours - last) < (rule.cooldown_minutes / 60.0):
                continue

            if evaluator.evaluate(rule.when):
                for action in rule.actions:
                    candidates.append(ActionCandidate(
                        source=f"rule:{rule.id}",
                        priority=rule.priority,
                        action=action,
                        reason=f"{rule.id} fired",
                    ))
                self.last_fired_at[rule.id] = elapsed_hours

        return sorted(candidates, key=lambda c: ("P0", "P1", "P2", "P3").index(c.priority))


class ActionCandidate(BaseModel):
    source: str
    priority: Priority
    action: ToolCall
    reason: str
```

### 5.4 競合解消ポリシー

| 競合 | 例 | 解消 |
|---|---|---|
| 同じアクチュエータへの異なる命令 | `set_perfusion_rate(7.0)` vs `set_perfusion_rate(0.0)` | 優先度が高い方を採用。同優先度ならレシピ > ルール、または安全側を選択 |
| ルールとレシピの両方で perfusion 変更 | ramp_perfusion vs osmolality_high | レシピの scheduled_action は基本、緊急ルール（P0/P1）はオーバーライド |
| feed と exchange_media の同時発火 | glucose_low + lactate_high | `action_planner` で依存関係を解決（exchange 後に feed すると希釈されるため順序付け） |
| 条件重複 | lactate_high と osmolality_high が両方発火 | 両アクションを候補に入れ、planner で sanitizer に通す |

---

## 6. イベントディスパッチャ

### 6.1 責務

`cell_culture.events.detect_events()` の出力を受け取り、L1 ルールエンジンが解釈しやすい形式に正規化する。

- イベント名の正規化（`lactate_high` 等）
- 抑制窓（suppression）の適用
- 優先度マッピング
- 継続時間条件の解釈支援（`for_minutes` 用にイベント履歴を保持）

### 6.2 実装

```python
# src/auto_cell/l1/event_dispatcher.py
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from auto_cell.plugins.cell_culture.events import EventResult


@dataclass
class EventHistory:
    event: str
    first_seen_at_hours: float
    last_seen_at_hours: float
    count: int = 1


class EventDispatcher:
    def __init__(self, suppression_defaults: dict[str, float]):
        """
        suppression_defaults: event -> suppression window in hours.
        """
        self.suppression_defaults = suppression_defaults
        self.active: dict[str, EventHistory] = {}

    def update(self, raw_events: list[EventResult], elapsed_hours: float) -> list[str]:
        """
        抑制を適用し、今サイクルで「新規または存続中（抑制期間内）」のイベント名を返す。
        """
        # 現在発生中のイベントをマーク
        seen_now = {e.name for e in raw_events if e.active}

        # 既存履歴を更新
        for name in seen_now:
            if name in self.active:
                self.active[name].last_seen_at_hours = elapsed_hours
                self.active[name].count += 1
            else:
                # 抑制期間中の再発火は無視
                pass

        # 新規イベント
        new_events = []
        for name in seen_now:
            if name not in self.active:
                self.active[name] = EventHistory(name, elapsed_hours, elapsed_hours)
                new_events.append(name)

        # 期限切れを削除
        window_hours = lambda n: self.suppression_defaults.get(n, 0.0)
        expired = [
            n for n, h in self.active.items()
            if elapsed_hours - h.last_seen_at_hours > window_hours(n)
        ]
        for n in expired:
            del self.active[n]

        # 存続中イベント名を返す
        return list(self.active.keys())
```

### 6.3 イベント→ルールのマッピング例

| イベント | 優先度 | 発火ルール例 |
|---|---|---|
| `do_low` | P0 | `emergency_do_low` |
| `contamination_suspected` | P0 | 緊急ホールド |
| `ph_out_of_range` | P1 | ガス setpoint 調整（ただし L0 PID が主） |
| `glucose_low` | P2 | `glucose_low_feed` |
| `lactate_high` | P1 | `lactate_high_exchange` |
| `osmolality_high` | P1 | perfusion 増加 / exchange |
| `aggregate_out_of_range` | P2 | 撹拌変更 / passage 検討 |
| `large_aggregate_high` | P1 | 撹拌増加 |
| `vcd_target_reached` | P1 | `passage_ready` 遷移トリガ |
| `shear_risk` | P1 | 撹拌減少 |

---

## 7. サイクル実行器

### 7.1 責務

- 一定周期（デフォルト 30 s）またはイベント駆動で L1 サイクルを実行
- Sense: `CellCultureEnv` を取得
- Decide: 状態機械遷移判定 → レシピアクション収集 → ルールエンジン評価 → イベントディスパッチャ更新 → アクションプランニング → sanitizer 通過
- Act: MQTT gateway へ cmd 発行、承認要求が必要な場合は `state/approval/{request_id}` を発行
- Log: event_store へサイクル結果を記録

### 7.2 実装

```python
# src/auto_cell/l1/cycle_executor.py
from __future__ import annotations

import time
from typing import Callable
from pydantic import BaseModel
from auto_cell.l1.recipe_engine import RecipeEngine
from auto_cell.l1.types import ToolCall, ActionCandidate
from auto_cell.plugins.cell_culture.environment import CellCultureEnv


class CycleResult(BaseModel):
    cycle: int
    elapsed_hours: float
    state_id: str
    sensor_snapshot: CellCultureEnv
    events: list[str]
    candidates: list[ActionCandidate]
    executed: list[ToolCall]
    rejected: list[ToolCall]
    approval_requested: list[ToolCall]


class L1CycleExecutor:
    def __init__(
        self,
        recipe_engine: RecipeEngine,
        get_env: Callable[[], CellCultureEnv],
        issue_command: Callable[[ToolCall, str], None],
        request_approval: Callable[[ToolCall, str], str],
        audit: Callable[[CycleResult], None],
        cycle_interval_seconds: float = 30.0,
    ):
        self.engine = recipe_engine
        self.get_env = get_env
        self.issue_command = issue_command
        self.request_approval = request_approval
        self.audit = audit
        self.cycle_interval_seconds = cycle_interval_seconds
        self.cycle = 0
        self.running = False

    def run_once(self) -> CycleResult:
        self.cycle += 1
        env = self.get_env()
        elapsed_hours = env.culture_age_h

        result = self.engine.step(self.cycle, elapsed_hours, env)

        for tc in result.executed:
            self.issue_command(tc, correlation_id=f"c{self.cycle}-{tc.tool}")
        for tc in result.approval_requested:
            self.request_approval(tc, correlation_id=f"c{self.cycle}-{tc.tool}")

        self.audit(result)
        return result

    def run_blocking(self, max_cycles: int | None = None) -> None:
        self.running = True
        while self.running:
            self.run_once()
            if max_cycles is not None and self.cycle >= max_cycles:
                break
            time.sleep(self.cycle_interval_seconds)

    def stop(self):
        self.running = False
```

### 7.3 イベント駆動モード

MQTT 側で `event` topic を受信した場合、即座に `run_once()` を呼び出す（ただし最短周期は 1 s、連続発火は debounce）。

```python
# pseudo in mqtt_bridge.py
def on_event_message(payload):
    if self.last_cycle_at and time.monotonic() - self.last_cycle_at < 1.0:
        return  # debounce
    asyncio.create_task(self.executor.run_once_async())
```

---

## 8. レシピエンジン（統合層）

### 8.1 責務

`RecipeEngine` は `RecipeStateMachine`, `RuleEngine`, `EventDispatcher`, `ActionPlanner`, sanitizer/tool 呼び出しを統合し、1 サイクルあたりの「実行すべきコマンド」「承認が必要なコマンド」を決定する。

### 8.2 実装

```python
# src/auto_cell/l1/recipe_engine.py
from __future__ import annotations

from auto_cell.l1.types import Recipe, Rule, ToolCall, ActionCandidate, Context
from auto_cell.l1.state_machine import RecipeStateMachine
from auto_cell.l1.rule_engine import RuleEngine
from auto_cell.l1.event_dispatcher import EventDispatcher
from auto_cell.l1.action_planner import ActionPlanner
from auto_cell.plugins.cell_culture.environment import CellCultureEnv
from auto_cell.plugins.cell_culture.sanitizer import validate_tool_call, SanitizerResult


class RecipeEngine:
    def __init__(
        self,
        recipe: Recipe,
        rules: list[Rule],
        suppression_defaults: dict[str, float],
        approvals: dict[str, str] | None = None,
    ):
        self.recipe = recipe
        self.rules = rules
        self.approvals = approvals or {}

        self.context = Context(
            recipe=recipe,
            env=None,  # type: ignore
            elapsed_hours=0.0,
            state_id=recipe.initial_state,
            event_log=[],
            approvals=self.approvals,
        )
        self.state_machine = RecipeStateMachine(recipe, self.context)
        self.rule_engine = RuleEngine(rules)
        self.dispatcher = EventDispatcher(suppression_defaults)
        self.planner = ActionPlanner()

    def step(self, cycle: int, elapsed_hours: float, env: CellCultureEnv) -> "CycleResult":
        self.context = self.context.model_copy(update={"env": env, "elapsed_hours": elapsed_hours})

        # 1. イベント更新
        raw_events = detect_events(env)  # from plugin
        active_events = self.dispatcher.update(raw_events, elapsed_hours)
        self.context.event_log = active_events

        # 2. 状態遷移
        transitions = self.state_machine.evaluate_transitions(elapsed_hours)
        if transitions:
            chosen = transitions[0]  # 複数ある場合は DSL 定義順の先頭
            self.state_machine.to_state(chosen, elapsed_hours=elapsed_hours)
            self.context.state_id = chosen

        # 3. timeout 処理
        timeout_target = self.state_machine.apply_timeout(elapsed_hours)
        if timeout_target:
            self.state_machine.to_state(timeout_target, elapsed_hours=elapsed_hours)
            self.context.state_id = timeout_target

        # 4. レシピからアクション収集
        recipe_candidates = self._collect_recipe_actions(elapsed_hours)

        # 5. ルールエンジン
        rule_candidates = self.rule_engine.evaluate(env, active_events, elapsed_hours, self.approvals)

        # 6. プランニング
        all_candidates = recipe_candidates + rule_candidates
        executed, rejected, approval_requested = self.planner.plan(
            all_candidates, env, self.context.state_id
        )

        return CycleResult(
            cycle=cycle,
            elapsed_hours=elapsed_hours,
            state_id=self.context.state_id,
            sensor_snapshot=env,
            events=active_events,
            candidates=all_candidates,
            executed=executed,
            rejected=rejected,
            approval_requested=approval_requested,
        )

    def _collect_recipe_actions(self, elapsed_hours: float) -> list[ActionCandidate]:
        state = self.recipe.get_state(self.context.state_id)
        actions: list[ActionCandidate] = []
        # entry actions は on_enter hook で pending_entry_actions に溜まっている
        for tc in self.state_machine.pending_entry_actions:
            actions.append(ActionCandidate(source="recipe:entry", priority="P2", action=tc, reason="state entry"))
        self.state_machine.pending_entry_actions.clear()

        # scheduled actions
        for sched in state.scheduled_actions:
            if self._is_due(sched, elapsed_hours):
                actions.append(ActionCandidate(source="recipe:scheduled", priority="P2", action=sched.action, reason=f"scheduled {sched.every_hours}h"))
        return actions

    def _is_due(self, sched, elapsed_hours: float) -> bool:
        if sched.every_hours is not None:
            return elapsed_hours % sched.every_hours < (self.cycle_interval_hours())
        if sched.at_hours is not None:
            return any(abs(elapsed_hours - h) < self.cycle_interval_hours() for h in sched.at_hours)
        return False

    def cycle_interval_hours(self) -> float:
        return 30.0 / 3600.0
```

---

## 9. アクションプランナー

### 9.1 責務

候補アクションを受け取り、以下を行う。

1. `value_ref` を実値に解決
2. `validate_tool_call()` で包絡線/ramp/Y-27632 強制を検証
3. 承認要否判定（包絡線外 or `trigger_passage` 等の高影響アクション）
4. 同アクチュエータへの複数命令を競合解消
5. 実行順序を決定（exchange → perfusion → feed → gas → agitation）

### 9.2 実装

```python
# src/auto_cell/l1/action_planner.py
from __future__ import annotations

from auto_cell.l1.types import ActionCandidate, ToolCall
from auto_cell.plugins.cell_culture.environment import CellCultureEnv
from auto_cell.plugins.cell_culture.sanitizer import validate_tool_call, ApprovalRequired


ORDER = ["exchange_media", "set_perfusion_rate", "feed", "set_gas_setpoint", "set_agitation_rpm", "trigger_passage", "take_sample", "notify", "log"]


class ActionPlanner:
    def plan(
        self,
        candidates: list[ActionCandidate],
        env: CellCultureEnv,
        state_id: str,
    ) -> tuple[list[ToolCall], list[ToolCall], list[ToolCall]]:
        # 優先度でソート済みを仮定
        executed: list[ToolCall] = []
        rejected: list[ToolCall] = []
        approval_requested: list[ToolCall] = []

        seen_tools: set[str] = set()  # 同 tool の重複は最初の候補のみ

        for cand in candidates:
            tool = cand.action.tool
            if tool in seen_tools and tool not in {"notify", "log", "feed"}:
                continue
            seen_tools.add(tool)

            result = validate_tool_call(tool, cand.action.args, env, state_id)
            if not result.ok:
                rejected.append(cand.action)
                continue

            if result.approval_required:
                approval_requested.append(cand.action)
                continue

            executed.append(cand.action)

        executed.sort(key=lambda tc: ORDER.index(tc.tool) if tc.tool in ORDER else 99)
        return executed, rejected, approval_requested
```

---

## 10. Manstein プロトコル DSL

### 10.1 プロトコル内容

Manstein 2021 プロトコルを L1 DSL で表現する。

- **播種密度**: 0.5×10⁶ cells/mL
- **pH**: 7.1（固定）
- **DO**: 40 %（0–72 h）→ 10 %（72 h 以降）
- **撹拌**: 80 rpm（固定）
- **灌流**: 0 vvd（seed 直後）→ 7 vvd（120 h 線形 ramp）
- **条件起動給餌**: glucose ≤ 1.8 mM で 200 mM glucose bolus
- **条件起動培地交換**: lactate ≥ 35 mM または osmolality ≥ 450 mOsm/kg
- **継代**: VCD ≥ 35×10⁶ cells/mL で passage_ready → 承認 → trigger_passage

### 10.2 DSL 例

```yaml
# config/recipes/manstein_phase1.yaml
recipe:
  id: manstein_phase1
  version: "0.1.0"
  title: "Manstein 2021 perfusion 0-7 vvd protocol"
  initial_state: seed

  setpoints:
    ph: { value: 7.1, unit: pH }
    do_early: { value: 40, unit: "%" }
    do_late: { value: 10, unit: "%" }
    temp: { value: 37, unit: degC }
    agitation: { value: 80, unit: rpm }

  variables:
    seed_density: { value: 0.5e6, unit: cells/mL }
    target_vcd: { value: 35.0e6, unit: cells/mL }
    max_perfusion: { value: 7.0, unit: vvd }
    perfusion_ramp_start_h: { value: 0.5, unit: h }
    perfusion_ramp_end_h: { value: 120.0, unit: h }

  states:
    seed:
      entry_actions:
        - tool: set_gas_setpoint
          args: { parameter: ph, value_ref: "setpoints.ph.value" }
        - tool: set_gas_setpoint
          args: { parameter: do, value_ref: "setpoints.do_early.value" }
        - tool: set_agitation_rpm
          args: { rpm_ref: "setpoints.agitation.value" }
        - tool: set_perfusion_rate
          args: { rate: 0.0, unit: vvd }
      exit_condition:
        elapsed_hours: { ge_ref: "variables.perfusion_ramp_start_h.value" }
      transitions:
        - target: perfusion_ramp

    perfusion_ramp:
      scheduled_actions:
        - every_hours: 1.0
          action:
            tool: ramp_perfusion
            args:
              start_h_ref: "variables.perfusion_ramp_start_h.value"
              end_h_ref: "variables.perfusion_ramp_end_h.value"
              start_rate: 0.0
              end_rate_ref: "variables.max_perfusion.value"
      transitions:
        - target: passage_ready
          condition:
            sensor: vcd
            ge_ref: "variables.target_vcd.value"
          timeout_hours: 168
          on_timeout: hold

    passage_ready:
      entry_actions:
        - tool: notify
          args: { priority: P1, message: "VCD target reached; awaiting passage approval" }
      transitions:
        - target: approved_passage
          condition:
            approval: trigger_passage
            state: approved
      timeout_minutes: 30
      on_timeout: hold

    approved_passage:
      entry_actions:
        - tool: trigger_passage
          args: { method: dissociate, add_rock_inhibitor: true }
      transitions:
        - target: reseed
          condition:
            event: passage_completed

    reseed:
      entry_actions:
        - tool: set_perfusion_rate
          args: { rate: 0.0 }
      transitions:
        - target: seed
          condition:
            event: reseed_completed

    hold:
      entry_actions:
        - tool: set_perfusion_rate
          args: { rate: 0.0 }
        - tool: notify
          args: { priority: P0, message: "Protocol entered hold state" }
```

```yaml
# config/recipes/manstein_rules.yaml
rules:
  - id: do_transition_day3
    priority: P2
    when:
      sensor: culture_age_h
      ge: 72.0
    actions:
      - tool: set_gas_setpoint
        args: { parameter: do, value_ref: "setpoints.do_late.value" }
    cooldown_minutes: 1440

  - id: glucose_low_bolus
    priority: P2
    when:
      sensor: glucose
      le: 1.8
      for_minutes: 5.0
    actions:
      - tool: feed
        args: { substance: glucose, concentration_mM: 200.0, target_bump_mM: 2.0 }
    cooldown_minutes: 30

  - id: lactate_high_exchange
    priority: P1
    when:
      sensor: lactate
      ge: 35.0
      for_minutes: 10.0
    actions:
      - tool: exchange_media
        args: { volume_ratio: 0.5 }
    cooldown_minutes: 60

  - id: osmolality_high_perfusion
    priority: P1
    when:
      sensor: osmolality
      ge: 450.0
      for_minutes: 10.0
    actions:
      - tool: set_perfusion_rate
        args: { rate_ref: "variables.max_perfusion.value" }
    cooldown_minutes: 60
```

### 10.3 `ramp_perfusion` ツール

`ramp_perfusion` は仮想的なツールで、サイクル毎に線形補間した perfusion 値を計算し `set_perfusion_rate` に変換する。`action_planner` 内で展開する。

```python
def expand_ramp_perfusion(args: dict, env, recipe, elapsed_hours: float) -> float:
    start_h = recipe.variables[args["start_h_ref"]].value
    end_h = recipe.variables[args["end_h_ref"]].value
    start_rate = args["start_rate"]
    end_rate = recipe.variables[args["end_rate_ref"]].value
    if elapsed_hours <= start_h:
        return start_rate
    if elapsed_hours >= end_h:
        return end_rate
    ratio = (elapsed_hours - start_h) / (end_h - start_h)
    return start_rate + (end_rate - start_rate) * ratio
```

---

## 11. L1 と plugin/tool/sanitizer の連携

### 11.1 呼び出し関係

```
┌─────────────────────────────────────┐
│         RecipeEngine.step()         │
└──────────────┬──────────────────────┘
               │
    ┌──────────▼──────────┐
    │ detect_events(env)  │  ← cell_culture.events
    └──────────┬──────────┘
               │ list[EventResult]
    ┌──────────▼──────────┐
    │   EventDispatcher   │
    └──────────┬──────────┘
               │ list[str]
    ┌──────────▼──────────┐
    │    RuleEngine       │  ← cell_culture.rules.yaml
    └──────────┬──────────┘
               │ ActionCandidate[]
    ┌──────────▼──────────┐
    │    ActionPlanner    │
    │  validate_tool_call │  ← cell_culture.sanitizer
    └──────────┬──────────┘
               │ executed / approval_requested / rejected
    ┌──────────▼──────────┐
    │   MQTT bridge /     │
    │   direct tool call  │  ← cell_culture.tools
    └─────────────────────┘
```

### 11.2 連携ルール

- `detect_events()` は `CellCultureEnv` のみを入力とし、L1 側で抑制履歴を管理する（plugin は無状態）。
- `validate_tool_call()` は `tool`, `args`, `env`, `state_id` を受け取り、`SanitizerResult(ok, approval_required, reason)` を返す。L1 は `approval_required=True` のものを承認フローに回す。
- `tool_handlers` は L1 からは直接呼ばず、MQTT `cmd` topic 経由またはテスト時の direct stub を通す。L1 は「コマンド発行主体」であり、実行主体は gateway/device 側。
- `build_culture_unit_summary()` は L3 LLM/HMI 用で、L1 サイクルには不要。ただし L1 のサイクル結果を summary の材料にすることがある。

---

## 12. L1 と MQTT/virtual_edge の連携

### 12.1 Topic 契約

| topic | 方向 | payload | 用途 |
|---|---|---|---|
| `cell/{cu}/telemetry/{device_id}/{function_id}` | edge → brain | `{value, unit, timestamp}` | センサ入力 |
| `cell/{cu}/event/{device_id}/{event_id}` | edge → brain | `{name, active, timestamp}` | イベント通知 |
| `cell/{cu}/cmd/{device_id}/{function_id}` | brain → edge | `{args, correlation_id, request_id, timestamp}` | 副作用コマンド |
| `cell/{cu}/ack/{device_id}/{function_id}` | edge → brain | `{status, result, correlation_id, timestamp}` | コマンド受理/結果 |
| `cell/{cu}/state/approval/{request_id}` | brain ↔ HMI | `{state, request_id, correlation_id, requested_by, timestamp}` | 承認状態 |
| `cell/{cu}/notify/hmi/{priority}` | brain → HMI | `{message, priority, source, timestamp}` | HMI 通知 |
| `cell/{cu}/state/program/{program_id}` | brain → HMI | `{phase, elapsed_hours, recipe_id}` | 現在 phase |

### 12.2 センサ取得フロー

1. `mqtt_bridge` が `telemetry/...` を subscribe し、`CellCultureEnv` の各フィールドを更新する。
2. 更新があるたびに `route_channel()` を呼び出し、無効値や単位変換を行う。
3. サイクル実行器は `get_env()` で最新の `CellCultureEnv` を取得する。

### 12.3 アクチュエータ送信フロー

1. `action_planner` が出力した `executed` コマンドを `issue_command()` が受け取る。
2. `MqttBridge.publish_cmd()` が `cmd/{device_id}/{function_id}` に JSON を publish。
3. `virtual_edge/dummy_bioreactor.py`（または実機 gateway）が cmd を受信し、`plant_model.step()` または実デバイスを駆動。
4. `ack` topic で結果を返す。
5. `correlation_id` で cmd/ack を紐付け、event_store に記録。

### 12.4 承認統合

```python
# src/auto_cell/l1/mqtt_bridge.py
import json
import uuid
from typing import Callable
import paho.mqtt.client as mqtt


class L1MqttBridge:
    def __init__(self, culture_unit_id: str, broker_host: str, port: int = 1883):
        self.cu = culture_unit_id
        self.client = mqtt.Client()
        self.client.on_message = self._on_message
        self.client.connect(broker_host, port)
        self._approval_callbacks: dict[str, Callable[[str], None]] = {}
        self._ack_callbacks: dict[str, Callable[[dict], None]] = {}

    def publish_cmd(self, tool_call: ToolCall, correlation_id: str | None = None) -> str:
        cid = correlation_id or str(uuid.uuid4())
        device_id, function_id = self._map_tool_to_function(tool_call.tool)
        topic = f"cell/{self.cu}/cmd/{device_id}/{function_id}"
        payload = {
            "args": tool_call.args,
            "correlation_id": cid,
            "request_id": str(uuid.uuid4()),
            "timestamp": utcnow_iso(),
        }
        self.client.publish(topic, json.dumps(payload))
        return cid

    def request_approval(self, tool_call: ToolCall, correlation_id: str | None = None) -> str:
        request_id = str(uuid.uuid4())
        topic = f"cell/{self.cu}/state/approval/{request_id}"
        payload = {
            "state": "requested",
            "request_id": request_id,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "requested_by": "l1_engine",
            "tool": tool_call.tool,
            "args": tool_call.args,
            "timestamp": utcnow_iso(),
        }
        self.client.publish(topic, json.dumps(payload))
        return request_id

    def _on_message(self, client, userdata, message):
        topic = message.topic
        payload = json.loads(message.payload)
        if "state/approval" in topic:
            request_id = topic.split("/")[-1]
            state = payload.get("state")
            cb = self._approval_callbacks.pop(request_id, None)
            if cb:
                cb(state)
        elif "/ack/" in topic:
            cid = payload.get("correlation_id")
            cb = self._ack_callbacks.pop(cid, None)
            if cb:
                cb(payload)

    def _map_tool_to_function(self, tool: str) -> tuple[str, str]:
        mapping = {
            "set_perfusion_rate": ("bioreactor", "PerfusionRateController"),
            "set_agitation_rpm": ("bioreactor", "AgitationController"),
            "set_gas_setpoint": ("bioreactor", "GasController"),
            "feed": ("dispense", "FeedPump"),
            "exchange_media": ("dispense", "MediaExchange"),
            "trigger_passage": ("bioreactor", "PassageMethod"),
            "take_sample": ("sampler", "TakeSample"),
        }
        return mapping.get(tool, ("bioreactor", tool))
```

### 12.5 virtual_edge dummy plant

`infra/virtual_edge/dummy_bioreactor.py` は MQTT を介して `plant_model.step()` を駆動する。

```python
# infra/virtual_edge/dummy_bioreactor.py
from sim.plant_model import step

class DummyBioreactor:
    def __init__(self, culture_unit_id: str):
        self.cu = culture_unit_id
        self.state = initial_state()

    def handle_cmd(self, tool: str, args: dict) -> dict:
        actuators = self._tool_to_actuators(tool, args)
        sensors = step(self.state, actuators, dt=30.0)
        return {"status": "ok", "sensors": sensors.model_dump()}

    def _tool_to_actuators(self, tool: str, args: dict):
        a = Actuators()
        if tool == "set_perfusion_rate":
            a.perfusion_rate_vvd = args["rate"]
        elif tool == "set_agitation_rpm":
            a.agitation_rpm = args["rpm"]
        elif tool == "set_gas_setpoint":
            if args["parameter"] == "do":
                a.do_setpoint = args["value"]
            elif args["parameter"] == "ph":
                a.ph_setpoint = args["value"]
        elif tool == "feed":
            if args["substance"] == "glucose":
                a.feed_glucose = args["target_bump_mM"]
        elif tool == "exchange_media":
            a.exchange_volume_ratio = args.get("volume_ratio", 0.5)
        return a
```

---

## 13. テスト計画

### 13.1 テストファイル構成

| ファイル | 内容 |
|---|---|
| `tests/l1/test_l1_recipe_loader.py` | DSL YAML 読み込み、バリデーション、value_ref 解決 |
| `tests/l1/test_l1_state_machine.py` | 状態遷移、timeout、entry/exit アクション |
| `tests/l1/test_l1_rule_engine.py` | 各ルール発火、クールダウン、優先度ソート |
| `tests/l1/test_l1_event_dispatcher.py` | 抑制窓、イベント履歴、debounce |
| `tests/l1/test_l1_action_planner.py` | 競合解消、承認要否、実行順序 |
| `tests/l1/test_l1_cycle_executor.py` | 同期サイクル、イベント駆動、承認統合 |
| `tests/l1/test_l1_recipe_engine.py` | Manstein DSL 統合、7 日間縮小シミュレーション |

### 13.2 状態遷移テスト例

```python
# tests/l1/test_l1_state_machine.py
import pytest
from auto_cell.l1.recipe_loader import load_recipe
from auto_cell.l1.state_machine import RecipeStateMachine
from auto_cell.l1.types import Context
from auto_cell.plugins.cell_culture.environment import CellCultureEnv


@pytest.fixture
def recipe():
    return load_recipe("config/recipes/manstein_phase1.yaml")


def test_seed_to_perfusion_ramp(recipe):
    env = CellCultureEnv(culture_age_h=0.6)
    ctx = Context(recipe=recipe, env=env, elapsed_hours=0.6, state_id="seed", event_log=[], approvals={})
    sm = RecipeStateMachine(recipe, ctx)
    targets = sm.evaluate_transitions(0.6)
    assert "perfusion_ramp" in targets


def test_perfusion_ramp_to_passage_ready(recipe):
    env = CellCultureEnv(culture_age_h=120.0, vcd=36e6)
    ctx = Context(recipe=recipe, env=env, elapsed_hours=120.0, state_id="perfusion_ramp", event_log=[], approvals={})
    sm = RecipeStateMachine(recipe, ctx)
    targets = sm.evaluate_transitions(120.0)
    assert "passage_ready" in targets
```

### 13.3 ルールテスト例

```python
# tests/l1/test_l1_rule_engine.py
import pytest
from auto_cell.l1.rule_engine import RuleEngine, Rule
from auto_cell.l1.types import ToolCall, SensorCondition
from auto_cell.plugins.cell_culture.environment import CellCultureEnv


RULES = [
    Rule(
        id="glucose_low",
        priority="P2",
        when=SensorCondition(sensor="glucose", op="le", value=1.8, for_minutes=5.0),
        actions=[ToolCall(tool="feed", args={"substance": "glucose"})],
    ),
]


def test_glucose_low_fires():
    engine = RuleEngine(RULES)
    env = CellCultureEnv(glucose=1.5, culture_age_h=24.0)
    cands = engine.evaluate(env, [], elapsed_hours=24.0)
    assert any(c.action.tool == "feed" for c in cands)


def test_glucose_normal_does_not_fire():
    engine = RuleEngine(RULES)
    env = CellCultureEnv(glucose=3.0, culture_age_h=24.0)
    cands = engine.evaluate(env, [], elapsed_hours=24.0)
    assert not any(c.action.tool == "feed" for c in cands)
```

### 13.4 サイクルテスト例

```python
# tests/l1/test_l1_cycle_executor.py
import pytest
from auto_cell.l1.cycle_executor import L1CycleExecutor
from auto_cell.l1.recipe_engine import RecipeEngine
from auto_cell.l1.recipe_loader import load_recipe, load_rules


def test_cycle_runs_without_approval():
    recipe = load_recipe("config/recipes/manstein_phase1.yaml")
    rules = load_rules("config/recipes/manstein_rules.yaml")
    engine = RecipeEngine(recipe, rules, suppression_defaults={})

    commands = []
    approvals = []

    def issue(tc, correlation_id):
        commands.append(tc.tool)

    def request(tc, correlation_id):
        approvals.append(tc.tool)

    class FakeEnv:
        culture_age_h = 0.6
        vcd = 0.6e6
        glucose = 5.0
        lactate = 5.0
        osmolality = 300.0

    exec_ = L1CycleExecutor(engine, get_env=lambda: FakeEnv(), issue_command=issue, request_approval=request, audit=lambda x: None)
    result = exec_.run_once()
    assert result.state_id == "perfusion_ramp"
    assert "set_gas_setpoint" in commands
```

### 13.5 決定性テスト

同一 `CellCultureEnv` 系列・同一レシピ・同一ルールセットを入力した場合、出力する `ToolCall` 系列が同一であることを保証する。

```python
def test_determinism(recipe_engine):
    env = CellCultureEnv(culture_age_h=10.0, glucose=1.5)
    r1 = recipe_engine.step(1, 10.0, env)
    r2 = recipe_engine.step(1, 10.0, env)
    assert [c.action.model_dump() for c in r1.candidates] == [c.action.model_dump() for c in r2.candidates]
```

---

## 14. 依存関係

### 14.1 Python パッケージ

`pyproject.toml` に以下を追加する。

```toml
[project.dependencies]
physical-ai-core = { path = "../physical-ai-core", editable = true }
scipy>=1.11
numpy>=1.26
pydantic>=2.0
transitions>=0.9
pyyaml>=6.0
paho-mqtt>=2.0
```

- `pydantic>=2.0`: DSL・CPP モデルの型安全
- `transitions>=0.9`: 状態機械
- `pyyaml>=6.0`: DSL YAML 読み込み
- `paho-mqtt>=2.0`: MQTT クライアント（MQTT 5.0 対応）

### 14.2 内部依存

- `src/auto_cell/plugins/cell_culture/environment.py`: `CellCultureEnv`
- `src/auto_cell/plugins/cell_culture/events.py`: `detect_events()`, suppression defaults
- `src/auto_cell/plugins/cell_culture/tools.py`: tool name → device mapping
- `src/auto_cell/plugins/cell_culture/sanitizer.py`: `validate_tool_call()`
- `sim/plant_model/`: `step()`（virtual_edge 経由）
- `src/auto_cell/audit/event_store.py`: サイクル結果の永続化

### 14.3 core 改修

physical-ai-core の cognitive loop 常駐を外し、L1 engine を plugin 呼び出し可能な形にする。具体的には：

- `WorldModel` から `domain_envs["cell_culture"]` を取得する IF は維持
- tool 呼び出しを MQTT `cmd` topic 発行に切り替える
- L3 LLM 起動をイベント駆動に変更

---

## 15. リスクと対応

| # | リスク | 影響 | 対応 |
|---|---|---|---|
| R1 | `transitions` の条件評価が状態機械内部で副作用を起こす | テスト・再現性 | 条件関数は純粋関数にし、entry/exit action は `ToolCall` 生成のみに限定。遷移実行前に `evaluate_transitions()` で予測可能 |
| R2 | DSL 文法の変更 | 後方互換性喪失 | `recipe_loader` にバージョンフィールドを持たせ、未知のキーは Pydantic `extra="forbid"` で早期検出。テストで全レシピを読み込む |
| R3 | ルール優先順位の誤設定 | 緊急事象への遅延 / 安全側動作の欠如 | P0 は常に最優先。同 tool への重複は planner で安全側を選択。レビュー基準文書を作成 |
| R4 | 承認フロー遅延 | サイクル停止 / timeout 誤発火 | `on_timeout` を安全側（hold/cancel）に設定。HMI 通知は即時。承認応答は非同期でサイクルは継続 |
| R5 | MQTT 非同期 request-response の複雑性 | テスト困難、ack 紛失 | まず同期ラッパで実装。correlation_id/request_id で紐付け。冪等性は request_id 重複チェック |
| R6 | `value_ref` の循環参照・未定義 | runtime error | ロード時に全 ref を解決可能か静的チェックする |
| R7 | plant_model の決定性 | golden test 破綻 | `numpy` 乱数シード固定、`scipy.solve_ivp` の solver/method 固定 |

---

## 16. 実装工数見積もり

Phase 1 Sprint 5（Week 5）〜 Sprint 6（Week 6）に実施。担当 1 名 + レビュー 1 名。

| 週 | タスク | 工数 | 完了基準 |
|---|---|---|---|
| Week 5 Day 1–2 | `l1/types.py`, `recipe_loader.py`, DSL スキーマ実装 | 2 日 | YAML 読み込み＋バリデーション pass |
| Week 5 Day 3–4 | `state_machine.py` 実装（transitions 利用） | 2 日 | seed→perfusion_ramp→passage_ready 遷移テスト pass |
| Week 5 Day 5 | `rule_engine.py` 実装 | 1 日 | glucose/lactate/osmolality トリガテスト pass |
| Week 6 Day 1 | `event_dispatcher.py` + `action_planner.py` | 1 日 | 抑制・競合解消テスト pass |
| Week 6 Day 2–3 | `cycle_executor.py` + `recipe_engine.py` 統合 | 2 日 | 1 サイクル step() が end-to-end で動作 |
| Week 6 Day 4 | `mqtt_bridge.py` + virtual_edge 結線 | 1 日 | dummy plant 経由で cmd/ack が往復 |
| Week 6 Day 5 | `config/recipes/manstein_*.yaml` 作成 + テスト追加 | 1 日 | `pytest tests/l1/` 全 pass |

**合計: 2 週間（1 名）**

並列作業:

- Week 5 中に cell_culture plugin（environment/events/tools/sanitizer）が凍結していることが前提。未確定の場合は仮 IF を作り後で差し替え（+1 日）。
- MQTT/virtual_edge は L1 エンジン完成後に本格結線するが、Week 5 から並行して topic 契約の stub を用意しておく。

---

## 17. 完了基準（Definition of Done）

1. `pytest tests/l1/` が全 pass する。
2. `config/recipes/manstein_phase1.yaml` + `manstein_rules.yaml` が読み込め、7 日間の縮小シミュレーション（例: 10 サイクル、30 s 周期相当）でエラーなく動作する。
3. `RecipeEngine.step()` の出力が、同一入力で同一 `ToolCall` 系列を返す（決定性テスト）。
4. `validate_tool_call()` を通過しないコマンドは `rejected` に入り、実行されない。
5. `trigger_passage` 等の高影響アクションは `approval_requested` に入り、`state/approval/{request_id}` が発行される。
6. virtual_edge 上で cmd/ack の往復が 1 サイクル以上確認できる。

---

## 18. 参照

- `docs/design/closed_loop_planning/05_implementation_plan_phase1.md`
- `docs/design/closed_loop_planning/06_critical_path_and_work_order.md`
- `docs/design/closed_loop_planning/03_swarm_findings_integration.md`
- `docs/design/closed_loop_planning/02_missing_assets_for_closed_loop.md`
- `docs/design/kg_to_auto_cell.md`
- `docs/design/adr/0001-control-architecture.md`
- `sim/plant_model/__init__.py`
- `src/auto_cell/plugins/cell_culture/`
