:# Phase 1 最終ワークストリーム統合

> 目的: 6 つの Agent 産出モジュール計画（M01–M06）を統合し、クリティカルパスを考慮した最終的な作業順序、インターフェース合意事項、次のアクションを確定する。
> 前提: `06_critical_path_and_work_order.md`、`module_plans/M01–M06.md`
> Date: 2026-06-30

---

## 1. Executive Summary

Phase 1 / v1（10 週間）の閉ループ実装を **6 つのワークストリーム**に分割し、各モジュールの詳細計画を Agent に委譲して作成した。本ドキュメントでは、それらを統合し、**クリティカルパス、並列化可能タスク、モジュール間インターフェース合意事項、最終作業順序**を確定する。

**結論**: 最短で閉ループを成立させるには、**plant_model → cell_culture plugin → L1 engine → MQTT/virtual_edge → HMI/approval/audit** の順に依存関係を解きながら、BO/LLM/imaging/confidence は並列で骨格化する。

---

## 2. ワークストリームとモジュール計画の対応

| ワークストリーム | モジュール計画 | 担当想定 | 週番号 | クリティカルパス |
|---|---|---|---|---|
| **WP-A** plant_model | M01 | 開発者 1 | Week 1–2 | ◎ |
| **WP-B** cell_culture plugin | M02 | 開発者 2 | Week 1–4 | ◎ |
| **WP-C** L1 engine | M03 | 開発者 3 | Week 3–6 | ◎ |
| **WP-D** MQTT / virtual_edge | M04 | 開発者 4 | Week 4–6 | ◎ |
| **WP-E** HMI / approval / audit | M05 | 開発者 5 | Week 5–7 | ◎（approval 部分） |
| **WP-F** BO / LLM / imaging / confidence | M06 | 開発者 6 | Week 7–10 | △（骨格のみ） |

---

## 3. 各モジュール計画の主要設計判断

### 3.1 M01 plant_model

| 項目 | 決定事項 |
|---|---|
| ファイル構成 | `sim/plant_model/{constants.py, state.py, manstein_ode.py, solver.py, factory.py, _compat.py}` + `__init__.py` |
| 主要 API | `PlantModel.step(actuators, dt) -> sensors` |
| ODE 項 | 6 項 Monod（VCD, glucose, lactate, glutamine, osmolality, aggregate）+ perfusion 希釈・供給項 |
| 決定性保証 | 固定初期状態、乱数不使用、ソルバー固定、`dense_output=False` |
| 初期状態 | `seed_state()` で 0.5×10⁶ cells/mL、viability 97%、E8 培地組成 |
| golden test | 7 日で VCD ~35×10⁶ ±15%、DO 40→10%、pH 7.1 |
| リスク | 原論文 Data S1（Berkeley Madonna コード）未取得のため、数式は推定形。`manstein_ode.py` のみ後で差し替え可能な構造 |

### 3.2 M02 cell_culture plugin

| 項目 | 決定事項 |
|---|---|
| ファイル構成 | `plugins/cell_culture/{environment.py, channels.py, events.py, tools.py, sanitizer.py, prompt.py, confidence.py, aggregate_imaging.py}` |
| `CellCultureEnv` | 全 CPP + CSPR 計算フィールド + large_aggregate_ratio + ammonia 参考値 |
| ramp 制限 | perfusion ±0.25 vvd/h、agitation ±5 rpm/h、DO ±5 %/h、pH ±0.05/h（S02 反映） |
| アンモニア | Warning 3 mM / Limit 5 mM を参考アラート。L1 トリガー化は保留 |
| イベント | 11 イベント（ph_out_of_range, do_low, lactate_high, glucose_low, glutamine_low, osmolality_high, aggregate_out_of_range, large_aggregate_high, vcd_target_reached, contamination_suspected, shear_risk） |
| ツール | set_perfusion_rate, set_agitation_rpm, feed, exchange_media, set_gas_setpoint, trigger_passage, take_sample |
| sanitizer | 包絡線・ramp 制限・Y-27632 強制 |
| 画像 | Cellpose ベース + scikit-image fallback |
| 注意 | `physical-ai-core` `DomainVertical` ABC 未確定のため、`__init__.py` に仮 IF を置き後で差し替え |

### 3.3 M03 L1 engine

| 項目 | 決定事項 |
|---|---|
| ファイル構成 | `src/auto_cell/l1/{types.py, recipe_loader.py, state_machine.py, rule_engine.py, event_dispatcher.py, action_planner.py, cycle_executor.py, recipe_engine.py, mqtt_bridge.py}` |
| DSL | YAML。states/transitions/actions/conditions/timeout。`value_ref` でセンサ値参照 |
| 状態機械 | `transitions` ライブラリ使用。seed → perfusion_ramp → passage_ready → approved_passage → reseed / hold |
| ルール | glucose/lactate/osmolality トリガー。優先度 P0–P3、クールダウン |
| サイクル | 30 s 周期またはイベント駆動。`CycleResult` 出力 |
| Manstein DSL | 灌流 0→7 vvd、固定設定点、条件起動給餌・交換を DSL 化 |
| 注意 | `l1/` をサブパッケージにし、将来 `l2_bayesian/` 等と並列 |

### 3.4 M04 MQTT / virtual_edge

| 項目 | 決定事項 |
|---|---|
| ファイル構成 | `src/auto_cell/gateway/{mqtt_client.py, request_response.py, correlation.py, idempotency.py, lads_opcua_client.py, sila_client.py}`、`infra/virtual_edge/{dummy_bioreactor.py, device_profile.py}` |
| MQTT | paho-mqtt v2、MQTT 5.0 Response Topic + Correlation Data |
| 冪等性 | `request_id` + TTL + `IdempotencyStore` |
| topic | `cell/{culture_unit_id}/{direction}/{category}/{device_id}/{function_id}/{aspect}` |
| virtual_edge | `dummy_bioreactor.py` が MQTT 経由で `plant_model.step()` を駆動 |
| LADS/SiLA2 | 抽象骨格のみ。実機接続は Phase 1.5+ |
| テスト | `amqtt` 埋め込みブローカー fixture |

### 3.5 M05 HMI / approval / audit

| 項目 | 決定事項 |
|---|---|
| ファイル構成 | `src/auto_cell/hmi/{approval_service.py, approval_api.py, approval_matrix.py, dashboard_service.py}`、`src/auto_cell/audit/{event_store.py, audit_log.py, tool_executor.py}`、`src/auto_cell/schemas/audit_events.py` |
| event_store | 1 run = 1 JSONL、append-only |
| audit_log | append-only + 軽量ハッシュチェーン |
| tool_executor | contextvars + dual-write で who/when/what/why をログ化 |
| 承認状態 | requested → approved/rejected/pending_timeout → executed/cancelled |
| API | FastAPI。approve/reject/pending + タイムアウト |
| マトリクス | `config/approval_matrix.yaml` で tool/条件 → 承認要否・タイムアウト・デフォルト |
| ダッシュボード | API ファースト。CPP 現在値・トレンド・phase・承認待ち |

### 3.6 M06 BO / LLM / imaging / confidence

| 項目 | 決定事項 |
|---|---|
| ファイル構成 | `src/auto_cell/l2_bayesian/{space.py, objective.py, optimizer.py, constants.py}`、`l3_orchestrator.py`、`plugins/cell_culture/{aggregate_imaging.py, confidence.py, prompts/v1/{system.jinja, summary.jinja}, llm_io_log.py}` |
| BO | Ax Service API を採用。`CultureSearchSpace`（Pydantic）→ Ax `SearchSpace` |
| 目的関数 | run 単位スカラ。重みは `config/bo_objective_weights.yaml` から注入 |
| LLM | Jinja2 プロンプトバージョニング + SHA256 ハッシュ。入出力ログ。非クリティカル用途限定ガード |
| 画像 | Cellpose lazy import + CPU fallback。平均径、大径割合、円形度、アスペクト比 |
| 信頼度 | GP 事後分散 → confidence score。PLS/DL 分岐のインターフェース |

---

## 4. モジュール間インターフェース合意事項

### 4.1 必ず合意が必要なインターフェース

| # | インターフェース | 関与モジュール | 合意事項 |
|---|---|---|---|
| 1 | `PlantModel.step()` | M01 ↔ M04 | 入力: `Actuators` dataclass、出力: `Sensors` dataclass、状態は内部保持 |
| 2 | `CellCultureEnv` | M02 ↔ M03, M05 | Pydantic model のフィールド名・単位・計算フィールドを統一 |
| 3 | `detect_events()` | M02 ↔ M03 | 戻り型: `list[CultureEvent]`。event_id、priority、suppress_window を含む |
| 4 | `tool_schemas` / `tool_handlers` | M02 ↔ M03, M05 | JSON schema + callable。`validate_tool_call` の入出力型を統一 |
| 5 | MQTT topic ペイロード | M03 ↔ M04 | cmd/ack/state/approval/notify の JSON スキーマを統一 |
| 6 | correlation_id / request_id | M04 ↔ M05 | 生成ルール、有効期限、紐付け方法 |
| 7 | event_store スキーマ | M05 ↔ 全モジュール | `AuditEvent` Pydantic model。who/when/what/why/approval_id |
| 8 | 承認状態 | M05 ↔ M03 | `ApprovalState` enum、`approval_service.get_state()` API |

### 4.2 インターフェース凍結タイミング

| インターフェース | 凍結週 | 理由 |
|---|---|---|
| `PlantModel.step()` | Week 2 | plant_model 完成時 |
| `CellCultureEnv` | Week 3 | plugin 全般の基盤 |
| `detect_events()` / `tool_schemas` | Week 4 | L1 状態機械・ルールエンジンの入力 |
| MQTT topic ペイロード | Week 4 | L1 + virtual_edge 結合の前提 |
| event_store / approval スキーマ | Week 5 | HMI/audit 実装の前提 |
| BO 探索空間 / 目的関数 | Week 8 | Phase 0 で重み合意済みの前提 |

---

## 5. 最終作業順序（ガント風）

```
Week:  1   2   3   4   5   6   7   8   9   10
       ───────────────────────────────────────
WP-A   [====]
WP-B   [==========]
WP-C       [==========]
WP-D           [==========]
WP-E               [========]
WP-F                   [========]
       ───────────────────────────────────────
Milestone:
  M1 Week 2  plant_model golden test pass
  M2 Week 4  plugin IF 凍結
  M3 Week 6  L1 + virtual_edge 結合
  M4 Week 7  HITL + ALCOA-lite
  M5 Week 9  BO/LLM/imaging/confidence 骨格
  M6 Week 10 7 日間 E2E 閉ループ pass
```

### 5.1 第 1 波：基盤（Week 1–2）

| 並列タスク | 担当 | 完了基準 |
|---|---|---|
| M01 plant_model 定数・ODE・step() IF | WP-A | `PlantModel.step()` が動作 |
| M01 golden test | WP-A | 7 日 35×10⁶ 軌道 pass |
| M02 `CellCultureEnv` 設計開始 | WP-B | フィールド確定 |
| M03 DSL 文法確定 | WP-C | YAML スキーマ v0.1 |
| M04 MQTT topic 契約確定 | WP-D | topic 一覧 YAML 化 |
| M05 event_store スキーマ確定 | WP-E | Pydantic model 確定 |

### 5.2 第 2 波：plugin 完成（Week 3–4）

| 並列タスク | 担当 | 完了基準 |
|---|---|---|
| M02 channels.py / events.py | WP-B | 全イベント判定テスト pass |
| M02 tools.py / sanitizer.py | WP-B | 全 tool schema + validate テスト pass |
| M03 状態機械実装 | WP-C | seed → reseed 遷移テスト pass |
| M04 MQTT client 実装 | WP-D | publisher/subscriber テスト pass |
| M05 audit_log 実装 | WP-E | append-only + ハッシュチェーン テスト pass |

**マイルストーン M2**: Week 4 終了時点で plugin IF 凍結。

### 5.3 第 3 波：L1 + 通信（Week 5–6）

| 並列タスク | 担当 | 完了基準 |
|---|---|---|
| M03 ルールエンジン + サイクル実行器 | WP-C | plant_model 上で L1 サイクル 1 step 実行 |
| M04 virtual_edge + correlation_id + 冪等性 | WP-D | dummy bioreactor 経由で L1–plant_model 通信 |
| M05 承認 state machine + tool_executor | WP-E | 承認状態が L1 実行判定に反映 |

**マイルストーン M3**: Week 6 終了時点で L1 + virtual_edge 結合。

### 5.4 第 4 波：HITL + ALCOA-lite（Week 7）

| 並列タスク | 担当 | 完了基準 |
|---|---|---|
| M05 承認キュー API + ダッシュボード骨格 | WP-E | approve/reject/timeout が L1 に反映 |
| M05 EBR-like レポート導出 | WP-E | 1 run = 1 report |
| M03 L1 + approval 統合 | WP-C | 包絡線外アクションが承認要求を発行 |

**マイルストーン M4**: Week 7 終了時点で HITL + ALCOA-lite。

### 5.5 第 5 波：BO / LLM / imaging / confidence（Week 8–9）

| 並列タスク | 担当 | 完了基準 |
|---|---|---|
| M06 L2 BO 骨格 | WP-F | 固定シード再現性テスト pass |
| M06 L3 LLM オーケストレータ骨格 | WP-F | プロンプトバージョニング + 入出力ログ |
| M06 Cellpose 画像解析 | WP-F | 凝集体メトリクス算出テスト pass |
| M06 信頼度スコア骨格 | WP-F | GP 事後分散 → confidence score |

**マイルストーン M5**: Week 9 終了時点で BO/LLM/imaging/confidence 骨格。

### 5.6 第 6 波：統合・E2E・文書化（Week 10）

| 並列タスク | 担当 | 完了基準 |
|---|---|---|
| 統合スクリプト | 全員 | `scripts/run_closed_loop_sim.py` で一括起動 |
| 7 日間 E2E run | 全員 | 目標軌道に近い VCD/DO/pH で完了 |
| 承認フロー E2E | 全員 | trigger_passage、包絡線外 setpoint の各パス |
| ALCOA-lite E2E | 全員 | 3+ run で監査ログ取得確認 |
| ドキュメント更新 | 全員 | README/ROADMAP 更新 |

**マイルストーン M6**: Week 10 終了時点で Phase 1 完了。

---

## 6. クリティカルパスの再確認

### 6.1 クリティカルパス上のタスク（詳細版）

```
Week 1:  M01 定数・状態・ODE 右辺
Week 2:  M01 step() IF + perfusion 項 + golden test
Week 3:  M02 CellCultureEnv + channels
Week 4:  M02 events + tools + sanitizer
Week 5:  M03 DSL パーサ + 状態機械
Week 6:  M03 ルールエンジン + サイクル実行器 + M04 virtual_edge 結合
Week 7:  M05 承認 state machine + tool_executor + L1 統合
Week 10: 7 日間 E2E 閉ループ
```

### 6.2 並列化可能なタスク

| タスク | 開始週 | 理由 |
|---|---|---|
| M03 DSL 文法確定 | Week 1 | M01 と並列 |
| M04 MQTT topic 契約 | Week 1 | M01 と並列 |
| M05 event_store スキーマ | Week 1 | M01 と並列 |
| M03 状態機械 | Week 3 | M02 B1/B2 完了後 |
| M04 MQTT client | Week 3 | topic 契約後 |
| M05 audit_log | Week 3 | event_store 後 |
| M06 BO/LLM/imaging/confidence | Week 7 | 閉ループ成立後に骨格化 |

---

## 7. リスクと対応（統合版）

| # | リスク | 影響 | 対応 | 担当 |
|---|---|---|---|---|
| 1 | physical-ai-core ABC 未確定 | WP-B, WP-C | `__init__.py` に仮 IF を置き、core 確定後に差し替え | WP-B, WP-C |
| 2 | Manstein ODE 数式の原典一致不確実 | WP-A | `manstein_ode.py` のみ差し替え可能な構造。Data S1 取得後に修正 | WP-A |
| 3 | plant_model 数値不安定 | WP-A | stiff なら LSODA/BDF。Week 1 内に試行 | WP-A |
| 4 | MQTT 非同期 request-response | WP-D, WP-C | まず同期ラッパで実装 | WP-D |
| 5 | 承認状態と L1 実行の整合 | WP-E, WP-C | 簡易 in-memory 状態機械から開始 | WP-E, WP-C |
| 6 | Cellpose 依存が重い | WP-F | scikit-image ベースの fallback を先に実装 | WP-F |
| 7 | BO 目的関数重み未決定 | WP-F | Phase 0 で必ず合意。暫定重みで開始 | PM |

---

## 8. 次のアクション（具体的）

### 8.1 Phase 0 で必ず解決

1. **BO 目的関数重み**: `config/bo_objective_weights.yaml` を研究者合意のもと作成
2. **承認タイムアウト値**: `config/approval_matrix.yaml` に記載
3. **DSL 文法 v0.1**: `config/recipes/manstein_phase1.yaml` のドラフト
4. **physical-ai-core 改修方針**: 仮 IF 定義 or core 改修計画

### 8.2 Week 1 から開始可能

1. `sim/plant_model/` 実装（M01）
2. `src/auto_cell/plugins/cell_culture/environment.py` 実装（M02）
3. `config/mqtt_topics.yaml` 作成（M04）
4. `src/auto_cell/schemas/audit_events.py` 作成（M05）

### 8.3 インターフェース凍結会議

- **Week 2 終了時**: `PlantModel.step()` IF レビュー
- **Week 4 終了時**: `CellCultureEnv` / `detect_events()` / `tool_schemas` / MQTT topic ペイロード 凍結会議
- **Week 5 終了時**: event_store / approval スキーマ 凍結会議

---

## 9. 作成ファイル一覧

```
docs/design/closed_loop_planning/
├── 01_roadmap_criticism_verification.md
├── 02_missing_assets_for_closed_loop.md
├── 03_swarm_findings_integration.md
├── 04_implementation_plan_overview.md
├── 05_implementation_plan_phase1.md
├── 06_critical_path_and_work_order.md
├── 07_final_workstream_integration.md  <-- 本ファイル
└── module_plans/
    ├── M01_plant_model_implementation_plan.md
    ├── M02_cell_culture_plugin_implementation_plan.md
    ├── M03_l1_engine_implementation_plan.md
    ├── M04_mqtt_virtual_edge_implementation_plan.md
    ├── M05_hmi_approval_audit_implementation_plan.md
    └── M06_bo_llm_imaging_implementation_plan.md
```

---

## 10. 参照

- `docs/design/closed_loop_planning/module_plans/M01_plant_model_implementation_plan.md`
- `docs/design/closed_loop_planning/module_plans/M02_cell_culture_plugin_implementation_plan.md`
- `docs/design/closed_loop_planning/module_plans/M03_l1_engine_implementation_plan.md`
- `docs/design/closed_loop_planning/module_plans/M04_mqtt_virtual_edge_implementation_plan.md`
- `docs/design/closed_loop_planning/module_plans/M05_hmi_approval_audit_implementation_plan.md`
- `docs/design/closed_loop_planning/module_plans/M06_bo_llm_imaging_implementation_plan.md`
- `docs/design/closed_loop_planning/06_critical_path_and_work_order.md`
- `docs/design/closed_loop_planning/05_implementation_plan_phase1.md`
