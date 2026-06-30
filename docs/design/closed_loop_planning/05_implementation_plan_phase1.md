# Phase 1 / v1 詳細実装計画

> 目的: `04_implementation_plan_overview.md` の Phase 1 を、スプリント単位のタスク・依存関係・完了基準に分解する。
> 期間: 2.5 ヶ月（10 週間）を想定
> Scope: iPSC 浮遊/凝集体バイオリアクター制御（Manstein 型灌流 0→7 vvd）
> 前提: `04_implementation_plan_overview.md`、ADR-0001

---

## 1. Phase 1 ゴール

1. `sim/plant_model` で Manstein 2021 ODE を実装し、7 日 35×10⁶ cells/mL 軌道を CI で再現する。
2. `src/auto_cell/plugins/cell_culture/` を実装する。
3. L1 決定的レシピ/ルールエンジンを実装する。
4. MQTT topic 契約と `infra/virtual_edge/` 仮想バイオリアクターを実装する。
5. HMI/承認フローの骨格を実装する。
6. ALCOA-lite 監査ログと event_store を実装する。
7. L2 BO 骨格と L3 LLM オーケストレータの薄い実装を行う。
8. **virtual_edge 上で 7 日間のシミュレーション閉ループ run を完了する。**

---

## 2. スプリント計画

### Sprint 0: Phase 0 成果物の確定（Week 0、計画前）

| # | タスク | 担当 | 完了基準 | 出力ファイル |
|---|---|---|---|---|
| S0-1 | BO 目的関数の重み合意 | 研究者 + PM | 重み文書に署名または承認 | `bo_objective_weights.md` |
| S0-2 | 承認タイムアウトポリシー確定 | UX + 研究者 | タイムアウト値とデフォルト動作を文書化 | `approval_timeout_policy.md` |
| S0-3 | L1 レシピ DSL v0.1 | 設計者 | YAML/JSON スキーマ確定 | `recipe_dsl_v0.1.md` |
| S0-4 | physical-ai-core 改修方針 | アーキテクト | 改修範囲と回避策を文書化 | `core_modification_plan.md` |
| S0-5 | 環境構築 | 全員 | `uv sync --extra dev`、pytest、ruff、mypy 動作 | — |

**依存**: なし

---

### Sprint 1: plant_model 基盤（Week 1）

**目標**: Manstein ODE の右辺と `step()` IF の骨格を完成させる。

| # | タスク | 担当 | 完了基準 |
|---|---|---|---|
| 1-1 | ODE 定数テーブル実装 | 開発者 | `MansteinConstants` dataclass。µmax, K_Glc, K_Lac, K_Gln, K_Osm, K_Agg, q_Glc, q_Lac, q_Gln |
| 1-2 | 状態ベクトル定義 | 開発者 | `PlantState`: VCD, viability, glucose, lactate, glutamine, osmolality, aggregate_diameter |
| 1-3 | ODE 右辺実装（perfusion 項除く） | 開発者 | 6 項 Monod モデル。原典 Table 1 と一致 |
| 1-4 | `step(actuators, dt) -> sensors` IF | 開発者 | scipy `solve_ivp` を使った離散時間ステップ |
| 1-5 | 初期状態ファクトリ | 開発者 | seed 密度 0.5×10⁶ cells/mL、培地組成、設定値 |

**テスト**: `tests/test_plant_model_basics.py`

**成果物**:
- `sim/plant_model/manstein_ode.py`（または `__init__.py` 内）
- `tests/test_plant_model_basics.py`

---

### Sprint 2: plant_model 灌流項と検証（Week 2）

**目標**: perfusion 項を追加し、7 日軌道 golden test を作成する。

| # | タスク | 担当 | 完了基準 |
|---|---|---|---|
| 2-1 | perfusion 項実装 | 開発者 | perfusion_rate_vvd による培地交換・代謝物希釈 |
| 2-2 | アクチュエータベクタ定義 | 開発者 | perfusion_rate, agitation_rpm, do_setpoint, ph_setpoint, feed_glucose, feed_glutamine |
| 2-3 | センサ出力定義 | 開発者 | vcd, viability, glucose, lactate, glutamine, osmolality, aggregate_diameter_um, do_percent, ph, temp_c |
| 2-4 | golden test 作成 | 開発者 | 7 日間シミュレーション。VCD ~35e6、DO 40→10%、pH 7.1 |
| 2-5 | 決定性テスト | 開発者 | 同一 actuators 系列 → 同一 sensors 軌道 |

**テスト**: `tests/test_plant_model.py`

**成果物**:
- `sim/plant_model/__init__.py`（完成）
- `tests/test_plant_model.py`
- CI 設定更新

---

### Sprint 3: cell_culture plugin データモデルとチャネル（Week 3）

**目標**: `CellCultureEnv` と channel routing を実装する。

| # | タスク | 担当 | 完了基準 |
|---|---|---|---|
| 3-1 | `CellCultureEnv` Pydantic model | 開発者 | 全 CPP フィールドを含む（S02 調査結果反映: CSPR、ammonia 参考値、large_aggregate_ratio） |
| 3-2 | `channel_config` | 開発者 | LADS Function 名とのマッピング |
| 3-3 | `route_channel` | 開発者 | MQTT topic → `CellCultureEnv` フィールド書込 |
| 3-4 | 更新された CPP 包絡線定義 | 開発者 | ramp 制限を S02 値に更新 |
| 3-5 | `CellCulturePlugin` ABC 実装骨格 | 開発者 | `DomainVertical` または core 改修後の IF に対応 |

**テスト**: `tests/plugins/test_cell_culture_env.py`

**成果物**:
- `src/auto_cell/plugins/cell_culture/environment.py`
- `src/auto_cell/plugins/cell_culture/channels.py`
- `tests/plugins/test_cell_culture_env.py`

**注意**: physical-ai-core の `DomainVertical` ABC が未確定の場合、仮 IF を作って後で差し替え。

---

### Sprint 4: cell_culture plugin イベントとツール（Week 4）

**目標**: イベント判定と副作用ツールを実装する。

| # | タスク | 担当 | 完了基準 |
|---|---|---|---|
| 4-1 | `detect_events` | 開発者 | 全イベント（ph_out_of_range, do_low, lactate_high, glucose_low, glutamine_low, osmolality_high, aggregate_out_of_range, large_aggregate_high, vcd_target_reached, contamination_suspected, shear_risk） |
| 4-2 | `event_descriptions` / `suppression_defaults` | 開発者 | 各イベントの説明と抑制窓 |
| 4-3 | `tool_schemas` | 開発者 | set_perfusion_rate, set_agitation_rpm, feed, exchange_media, set_gas_setpoint, trigger_passage, take_sample |
| 4-4 | `tool_handlers` | 開発者 | 各 tool の模擬実行（plant_model 用） |
| 4-5 | `validate_tool_call` | 開発者 | 包絡線・ramp 制限・Y-27632 強制 |

**テスト**: `tests/plugins/test_cell_culture_events.py`, `tests/plugins/test_cell_culture_tools.py`

**成果物**:
- `src/auto_cell/plugins/cell_culture/events.py`
- `src/auto_cell/plugins/cell_culture/tools.py`
- `src/auto_cell/plugins/cell_culture/sanitizer.py`

---

### Sprint 5: L1 レシピ/状態機械/ルールエンジン（Week 5）

**目標**: L1 決定制御コアを実装する。

| # | タスク | 担当 | 完了基準 |
|---|---|---|---|
| 5-1 | レシピ DSL パーサ | 開発者 | YAML/JSON から状態・遷移・アクションを読込 |
| 5-2 | 状態機械エンジン | 開発者 | seed → perfusion_ramp → passage_ready → approved_passage → reseed / hold |
| 5-3 | ルールエンジン | 開発者 | glucose/lactate/osmolality トリガーで perfusion/feed/exchange を決定 |
| 5-4 | イベントディスパッチャ | 開発者 | 競合イベントの優先順位付け |
| 5-5 | Manstein プロトコル DSL | 開発者 | 灌流 0→7 vvd、固定設定点、条件起動給餌を DSL 化 |

**テスト**: `tests/test_l1_state_machine.py`, `tests/test_l1_rule_engine.py`

**成果物**:
- `src/auto_cell/l1_state_machine.py`
- `src/auto_cell/l1_rule_engine.py`
- `config/manstein_recipe.yaml`

---

### Sprint 6: L1 サイクル実行器と MQTT / virtual_edge（Week 6）

**目標**: L1 サイクルを回し、virtual_edge 経由で plant_model と通信する。

| # | タスク | 担当 | 完了基準 |
|---|---|---|---|
| 6-1 | L1 サイクル実行器 | 開発者 | 30 s+ 周期またはイベント駆動でサイクルを回す |
| 6-2 | MQTT topic 契約実装 | 開発者 | telemetry/event/cmd/ack/program/state/approval/notify/hmi |
| 6-3 | correlation_id 管理 | 開発者 | cmd/ack/approval の紐付け |
| 6-4 | 冪等性実装 | 開発者 | request_id による重複実行防止 |
| 6-5 | virtual_edge dummy plant | 開発者 | MQTT 経由で plant_model のセンサ/アクチュエータを模擬 |
| 6-6 | L1 + virtual_edge 統合 | 開発者 | L1 が dummy plant のセンサを読み、アクチュエータを駆動 |

**テスト**: `tests/test_l1_cycle.py`, `tests/test_virtual_edge.py`, `tests/test_mqtt_idempotency.py`

**成果物**:
- `src/auto_cell/l1_recipe_engine.py`
- `src/auto_cell/gateway/mqtt_client.py`
- `infra/virtual_edge/dummy_bioreactor.py`
- `config/mqtt_topics.yaml`

---

### Sprint 7: HMI / 承認フロー / ALCOA-lite（Week 7）

**目標**: 承認ワークフローと監査ログを実装する。

| # | タスク | 担当 | 完了基準 |
|---|---|---|---|
| 7-1 | 承認状態管理 | 開発者 | requested → approved/rejected/pending_timeout → executed/cancelled |
| 7-2 | 承認キュー API | 開発者 | approve/reject API、タイムアウト処理 |
| 7-3 | ダッシュボード骨格 | フロントエンド | CPP 現在値・トレンド・phase・承認待ち件数 |
| 7-4 | event_store スキーマ | 開発者 | イベント・コマンド・承認・テレメトリの統一スキーマ |
| 7-5 | audit_log 実装 | 開発者 | append-only + ハッシュチェーン（軽量版） |
| 7-6 | tool_executor ラッパ | 開発者 | 全 tool 呼び出しを who/when/what/why でログ化 |

**テスト**: `tests/test_approval_flow.py`, `tests/test_audit_log.py`

**成果物**:
- `src/auto_cell/hmi/approval_service.py`
- `src/auto_cell/hmi/dashboard.py`
- `src/auto_cell/audit/event_store.py`
- `src/auto_cell/audit/audit_log.py`
- `src/auto_cell/audit/tool_executor.py`

---

### Sprint 8: L2 BO 骨格と L3 LLM オーケストレータ（Week 8）

**目標**: run 間最適化と薄い LLM 層を実装する。

| # | タスク | 担当 | 完了基準 |
|---|---|---|---|
| 8-1 | BO ライブラリ導入 | 開発者 | Ax または BoTorch を依存関係に追加 |
| 8-2 | 探索空間 Pydantic model | 開発者 | seeding_density, initial_glucose, perfusion_ramp_profile, max_perfusion_rate, agitation_base_rpm, DO_transition, Y-27632_conc |
| 8-3 | 目的関数実装 | 開発者 | Phase 0 で合意した重み |
| 8-4 | 制約実装 | 開発者 | CPP 包絡線、ramp 制限を Safe BO 制約として表現 |
| 8-5 | BO 再現性テスト | 開発者 | 固定シードで同一提案 |
| 8-6 | L3 トリガー判定 | 開発者 | 承認仲介、曖昧知覚、新規例外で起動 |
| 8-7 | プロンプトテンプレート | 開発者 | システムプロンプト + 状態要約 |
| 8-8 | 入出力ログ | 開発者 | 思考・ツール呼び出し・根拠を記録 |

**テスト**: `tests/test_bo_reproducibility.py`, `tests/test_l3_orchestrator.py`

**成果物**:
- `src/auto_cell/l2_bayesian/optimizer.py`
- `src/auto_cell/l2_bayesian/objective.py`
- `src/auto_cell/l2_bayesian/space.py`
- `src/auto_cell/l3_orchestrator.py`
- `src/auto_cell/plugins/cell_culture/prompt.py`

---

### Sprint 9: 画像解析と信頼度スコア（Week 9）

**目標**: at-line 凝集体画像解析と信頼度スコア層を実装する。

| # | タスク | 担当 | 完了基準 |
|---|---|---|---|
| 9-1 | Cellpose 統合 | 開発者 | at-line 明視野/位相差画像のセグメンテーション |
| 9-2 | 凝集体メトリクス算出 | 開発者 | 平均径、大径割合（>400 µm）、円形度、アスペクト比 |
| 9-3 | L1 イベント統合 | 開発者 | `aggregate_out_of_range`, `large_aggregate_high` |
| 9-4 | 画像ログ | 開発者 | raw 画像・解析結果を保存 |
| 9-5 | 信頼度スコア骨格 | 開発者 | GP 事後分散からの信頼度。低信頼度で HITL エスカレーション |
| 9-6 | HMI 信頼度表示 | フロントエンド | 信頼度スコアと根拠の可視化 |

**テスト**: `tests/test_aggregate_imaging.py`, `tests/test_confidence_score.py`

**成果物**:
- `src/auto_cell/plugins/cell_culture/aggregate_imaging.py`
- `src/auto_cell/plugins/cell_culture/confidence.py`

---

### Sprint 10: 統合・E2E テスト・文書化（Week 10）

**目標**: virtual_edge 上で 7 日間の閉ループ run を完了し、Phase 1 終了条件を満たす。

| # | タスク | 担当 | 完了基準 |
|---|---|---|---|
| 10-1 | 統合スクリプト | 開発者 | virtual_edge + L1 + plant_model + HMI/承認を一括起動 |
| 10-2 | 7 日間 E2E シミュレーション | 全員 | 7 日間 run を完了。目標軌道に近い VCD/DO/pH |
| 10-3 | 承認フロー E2E テスト | 全員 | trigger_passage、包絡線外 setpoint の承認・拒否・タイムアウト |
| 10-4 | ALCOA-lite E2E テスト | 全員 | 全副作用ツールの監査ログ取得を 3+ run で確認 |
| 10-5 | ドキュメント更新 | 全員 | README、ROADMAP.md、設計文書への反映 |
| 10-6 | Phase 1 レビュー | 全員 | Phase 1 移行条件をすべて満たす |

**成果物**:
- `scripts/run_closed_loop_sim.py`
- 更新された `README.md`
- 更新された `ROADMAP.md`
- Phase 1 完了レポート

---

## 3. Phase 1 タスク依存関係図

```
Sprint 0: 未決事項解消 ─────────────────────────────────────┐
                                                            │
Sprint 1: plant_model 基盤 ──▶ Sprint 2: plant_model 完成    │
                                                            │
Sprint 3: plugin env/channels ──▶ Sprint 4: plugin events/tools/sanitizer
                                                            │
Sprint 2 + Sprint 4 ──▶ Sprint 5: L1 state machine/rules    │
                                                            │
Sprint 5 ──▶ Sprint 6: L1 cycle + MQTT/virtual_edge         │
                                                            │
Sprint 6 ──▶ Sprint 7: HMI/approval + ALCOA-lite            │
                                                            │
Sprint 7 ──▶ Sprint 8: L2 BO + L3 LLM                       │
                                                            │
Sprint 8 ──▶ Sprint 9: imaging + confidence                 │
                                                            │
Sprint 9 ──▶ Sprint 10: E2E integration + docs              │
```

---

## 4. 週次ミーテストン推奨トピック

| Week | トピック |
|---|---|
| 1 | plant_model 定数・IF レビュー |
| 2 | Manstein 軌道 golden test レビュー |
| 3 | `CellCultureEnv` フィールドレビュー（S02 反映確認） |
| 4 | イベント・ツール・sanitizer レビュー |
| 5 | DSL 文法・状態機械レビュー |
| 6 | MQTT topic 契約・virtual_edge レビュー |
| 7 | 承認フロー・ALCOA-lite レビュー |
| 8 | BO 目的関数・L3 権限制限レビュー |
| 9 | 画像解析・信頼度スコアレビュー |
| 10 | Phase 1 完了レビュー・Phase 1.5 計画 |

---

## 5. Phase 1 完了条件（Phase 1.5 移行条件）

| # | 条件 | 確認方法 |
|---|---|---|
| 1 | plant_model CI 成功 | `pytest tests/test_plant_model.py` が pass |
| 2 | L1 決定性検証 | `pytest tests/test_l1_*` が pass |
| 3 | ALCOA-lite 運用 | `pytest tests/test_audit_log.py` + 3+ E2E run で確認 |
| 4 | HITL 承認フロー | `pytest tests/test_approval_flow.py` + 手動デモ |
| 5 | シミュレーション閉ループ | `scripts/run_closed_loop_sim.py` で 7 日 run 完了 |
| 6 | BO 骨格完成 | `pytest tests/test_bo_reproducibility.py` が pass |

---

## 6. リスクと対応（Phase 1 内）

| # | リスク | 影響 | 対応 |
|---|---|---|---|
| R1 | physical-ai-core の `DomainVertical` ABC が未整備 | Sprint 3 以降の遅延 | 仮 IF を作り、core 確定後に差し替え。S0-4 で改修方針確定 |
| R2 | Manstein ODE の数値安定性 | Sprint 2 遅延 | 離散化方法を検討。stiff ODE の場合は BDF/LSODA |
| R3 | MQTT 非同期 request-response の複雑性 | Sprint 6 遅延 | まず同期ラッパで実装し、非同期は後段 |
| R4 | 承認フローの状態管理の複雑性 | Sprint 7 遅延 | シンプルな in-memory 状態機械から開始 |
| R5 | Cellpose 依存の追加 | Sprint 9 遅延 | 依存が重い場合は scikit-image ベースの簡易セグメンテーションから開始 |

---

## 7. 推奨ツール・ライブラリ

| 用途 | 候補 | 備考 |
|---|---|---|
| ODE 求解 | scipy `solve_ivp` | 決定性・再現性重視 |
| 設定管理 | Pydantic + YAML | 型安全 |
| MQTT | paho-mqtt | MQTT 5.0 対応 |
| 状態機械 | transitions（Python）または自前 | シンプルさ優先 |
| BO | Ax（Meta） | 高レベル API、制約対応 |
| 画像解析 | Cellpose 2.0/3.0 | 明視野/位相差に強い |
| テスト | pytest, pytest-asyncio | 非同期 MQTT テスト用 |
| Lint/型 | ruff, mypy | 既存プロジェクトと統一 |

---

## 8. 参照

- `docs/design/closed_loop_planning/04_implementation_plan_overview.md`
- `docs/design/closed_loop_planning/03_swarm_findings_integration.md`
- `docs/design/adr/0001-control-architecture.md`
- `docs/design/kg_to_auto_cell.md`
- `docs/design/roadmap.md`
- `docs/design/requirements.md`
