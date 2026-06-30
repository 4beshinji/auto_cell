# auto_cell A 層 閉ループ実装計画（Overview）

> 目的: Agent Swarm 調査（S01–S06）と既存設計文書を基に、auto_cell A 層で Sense-Decide-Act ループを閉じるための段階的・検証可能な実装計画を示す。
> Scope: iPSC 浮遊/凝集体バイオリアクター制御（Manstein 型灌流 0→7 vvd）
> 前提: ADR-0001、requirements.md、kg_to_auto_cell.md
> Date: 2026-06-30

---

## 1. 計画の概要

### 1.1 採用アーキテクチャ

ADR-0001（Accepted）に従い、L0–L3 分離を採用する。

| 層 | 主体 | 役割 | 実装方針 |
|---|---|---|---|
| **L0** | デバイス局所 PID | 温度/pH/DO/撹拌の高速安全ループ | デバイス側または gateway 経由。ブレインは設定点のみ変更 |
| **L1** | 決定的レシピ/ルールエンジン | 灌流/給餌/撹拌/サンプリング/継代の監督制御 | Python state machine + YAML/JSON DSL + ルールエンジン |
| **L2** | ベイズ最適化 | run 間のパラメータ探索 | Ax または BoTorch。`sim/plant_model` を多忠実度の低忠実度評価に使用 |
| **L3** | 薄い LLM オーケストレータ | 承認仲介、曖昧知覚解釈、新規例外、研究者対話 | イベント駆動・非常駐。非クリティカル用途限定 |

### 1.2 計画のフェーズ構成

| フェーズ | 期間目安 | 主要成果物 | ゴール |
|---|---|---|---|
| **Phase 0** | 1–2 週間 | 設計仕様確定、依存関係整理 | 実装前の未決事項解消 |
| **Phase 1 / v1** | 2–4 ヶ月 | L1 決定的コア、Manstein ODE、plugin、MQTT 契約、HMI/承認、ALCOA-lite | シミュレーション上で閉ループ運転 |
| **Phase 1.5** | 4–6 ヶ月 | Raman 観測/校正計画、画像定量化、BO 運用開始 | 実 run 前のデータ収集体制 |
| **Phase 2** | 6–18 ヶ月 | MPC シミュレーション、Raman アドバイザリ、GP バイアス補正、信頼度スコア | シミュレーション＋実 run 探索 |
| **Phase 3** | 18–36 ヶ月 | 多変数適応 MPC、Hybrid ODE+NN、Raman 閉ループ、DL 品質代理指標 | 適応制御と GMP 移行準備 |

---

## 2. Phase 0：実装前準備（1–2 週間）

### 2.1 未決事項の解消

| # | タスク | 担当 | 完了基準 |
|---|---|---|---|
| P0-1 | BO 目的関数の重みを研究者と合意 | 研究者 + PM | 目的関数 `J = yield^a × viability^b × pluripotency^c × aggregate_score^d × cost^e` の重み確定 |
| P0-2 | 承認タイムアウト値の初期値設定 | UX + 研究者 | 包絡線外 setpoint=10 min, trigger_passage=30 min, BO 提案=24 h を文書化 |
| P0-3 | L1 レシピ DSL 文法を確定 | 設計者 | YAML/JSON スキーマ v0.1 を作成 |
| P0-4 | physical-ai-core 改修方針確定 | アーキテクト | cognitive loop の常駐解除またはイベント駆動化の設計方針を確定 |
| P0-5 | 開発・テスト環境整備 | 開発者 | `uv sync --extra dev`、pytest、ruff、mypy が動作 |

### 2.2 成果物

- `docs/design/closed_loop_planning/phase0_decisions.md`
- `docs/design/closed_loop_planning/recipe_dsl_v0.1.md`
- `docs/design/closed_loop_planning/bo_objective_weights.md`
- `docs/design/closed_loop_planning/approval_timeout_policy.md`

---

## 3. Phase 1 / v1：決定的閉ループコア（2–4 ヶ月）

### 3.1 目標

- `sim/plant_model` の Manstein ODE を実装し、7 日 35×10⁶ cells/mL 軌道を CI で再現する。
- `src/auto_cell/plugins/cell_culture/` を実装する。
- L1 決定的レシピ/ルールエンジンを実装する。
- MQTT topic 契約と `infra/virtual_edge/` 仮想バイオリアクターを実装する。
- HMI/承認フローの骨格を実装する。
- ALCOA-lite 監査ログと event_store を実装する。
- L2 BO 骨格と L3 LLM オーケストレータの薄い実装を行う。

### 3.2 主要モジュール

| モジュール | 内容 | 優先度 |
|---|---|---|
| `sim/plant_model/` | Manstein 2021 6 項 Monod ODE + perfusion 項 + `step()` IF | 最高 |
| `plugins/cell_culture/` | environment/channels/events/tools/sanitizer/prompt/confidence/aggregate_imaging | 最高 |
| `l1_recipe_engine/` | DSL パーサ、状態機械、ルールエンジン、サイクル実行器 | 最高 |
| `gateway/` | MQTT client、LADS/OPC-UA/SiLA2 骨格 | 高 |
| `infra/virtual_edge/` | MQTT 経由 dummy plant | 高 |
| `hmi/` | 承認サービス、ダッシュボード骨格 | 高 |
| `audit/` | event_store、audit_log、tool_executor | 高 |
| `l2_bayesian/` | Ax/BoTorch ラッパ、探索空間、目的関数、制約 | 高 |
| `l3_orchestrator.py` | イベント駆動 LLM、プロンプトバージョニング、入出力ログ | 中 |

### 3.3 Phase 1 移行条件

| # | 条件 | 数値基準 |
|---|---|---|
| 1 | plant_model CI 成功 | 7 日 35×10⁶ cells/mL 軌道を再現 |
| 2 | L1 決定性検証 | 全イベント応答の単体テスト pass |
| 3 | ALCOA-lite 運用 | 全副作用ツールの監査ログ取得を確認 |
| 4 | HITL 承認フロー | 承認・拒否・タイムアウトの各パスを PoC 完了 |
| 5 | シミュレーション閉ループ | virtual_edge 上で 7 日間の run を完了 |
| 6 | BO 骨格完成 | 固定シード再現性テスト pass |

詳細は `05_implementation_plan_phase1.md` を参照。

---

## 4. Phase 1.5：実 run 準備（4–6 ヶ月）

### 4.1 目標

- Raman 観測・校正計画を開始する。
- at-line 凝集体画像を運用し、offline 正解ラベルを蓄積する。
- BO をシミュレーション/少数 run で試行する。
- LADS/SiLA2 gateway を実機接続準備する。

### 4.2 主要タスク

| # | タスク | 詳細 | 完了基準 |
|---|---|---|---|
| P1.5-1 | Raman 観測モジュール | スペクトル記録、Nova FLEX2 正解ラベル紐付け | 1+ バッチでデータ取得 |
| P1.5-2 | Raman 前処理パイプライン | SNV/MSC/EMSC、Savitzky-Golay、水ピーク内部標準 | コード完成 |
| P1.5-3 | 画像定量化運用 | at-line 画像の自動解析、日次レポート | 5+ run で運用 |
| P1.5-4 | BO 試行 | sim/plant_model 上でパラメータ探索 | 目的関数の感度分析 |
| P1.5-5 | LADS/SiLA2 gateway PoC | 実機またはベンダーシミュレータ接続 | 1–2 Function で読み書き |
| P1.5-6 | 信頼度スコア v1 | GP 事後分散からの信頼度 | HMI 表示 |

---

## 5. Phase 2：シミュレーションとアドバイザリ（6–18 ヶ月）

### 5.1 目標

- `sim/plant_model` 上で MPC シミュレーションを開始する。
- Raman PLS モデルをアドバイザリ入力として運用する。
- plant_model を GP バイアス補正で拡張する。
- 凝集体画像メトリクスを BO 入力に統合する。

### 5.2 主要タスク

| # | タスク | 詳細 | 完了基準 |
|---|---|---|---|
| P2-1 | MPC シミュレータ | do-mpc + CasADi + Manstein ODE | plant_model 上で 7 日間制約充足率 >95% |
| P2-2 | MPC アドバイザリ | perfusion rate の最適軌道を提示、承認後に L1 へ反映 | 3+ run で試行 |
| P2-3 | Raman PLS アドバイザリ | glucose/lactate 推定値を HMI 表示 | 5+ バッチ校正、RMSEP <15% |
| P2-4 | GP バイアス補正 | plant_model の予測バイアスを GP で補正 | 30+ run データで確認 |
| P2-5 | 多忠実度 BO | plant_model を低忠実度、実 run を高忠実度 | 実 run 数削減効果確認 |
| P2-6 | 信頼度スコア v2 | PLS Q 残差/Hotelling T² 追加 | 低信頼度で Nova 優先 |
| P2-7 | ドリフト監視 | 入力分布・性能劣化検知 | 1+ ドリフト検知テスト |
| P2-8 | XAI v1 | BO 獲得関数説明、PLS 重要変数 | HMI 表示 |

### 5.3 移行条件（Phase 3 へ）

| # | 条件 | 数値基準 |
|---|---|---|
| 1 | run 蓄積 | 30+ run（同一プロトコル・細胞株系） |
| 2 | MPC シミュレーション | plant_model 上で 7 日間制約充足率 >95% |
| 3 | Raman 校正 | 5+ バッチで PLS モデル構築、予測誤差が用途許容範囲内 |
| 4 | 画像定量化 | 平均径・大径割合の at-line 自動計測を 5+ run で運用 |
| 5 | 静的決定論的証明 | L2 BO の再現性テストを CI 化、モデルカードを全バージョンで作成 |
| 6 | 信頼度スコア | 低信頼度エスカレーションの感度分析を実施 |
| 7 | BO 目的関数 | 研究者合意済みの重みで 3+ run の最適化試行 |

---

## 6. Phase 3：適応制御と GMP 移行準備（18–36 ヶ月）

### 6.1 目標

- 多変数適応 MPC を実 run に導入する。
- Hybrid ODE+NN デジタルツインを運用化する。
- Raman を L1 閉ループ入力に昇格する。
- DL 品質代理指標を BO 目的関数に統合する。
- GMP IQ/OQ/PQ 移行準備を開始する。

### 6.2 主要タスク

| # | タスク | 詳細 | 完了基準 |
|---|---|---|---|
| P3-1 | 多変数適応 MPC | perfusion + agitation + DO setpoint + bolus feed | 実 run で目標軌道追従誤差 <10% |
| P3-2 | Hybrid ODE+NN | Manstein ODE + NN 補正項 | sim/real gap <20% |
| P3-3 | Raman 閉ループ v2 | glucose/lactate 推定値を L1 フィードバックへ自動反映 | 24 h 連続運転で drift 検知可能 |
| P3-4 | DL 品質代理指標 | 凝集体画像 DL で未分化/自発分化を推定 | AUC >0.8 |
| P3-5 | 多忠実度 BO 本格運用 | Tier2 plant + 実 run | 実 run 数を半減しつつ同程度の最適化性能 |
| P3-6 | 経済 MPC | 培地コスト・培養時間を目的関数に統合 | 研究者承認下で試行 |
| P3-7 | GMP 移行準備 | IQ/OQ/PQ 文書、電子署名、完全職員独立性、WORM | 品質保証部門承認 |

---

## 7. 主要ファイル・ディレクトリ構成

```
auto_cell/
├── src/auto_cell/
│   ├── __init__.py
│   ├── l1_recipe_engine.py
│   ├── l1_state_machine.py
│   ├── l1_rule_engine.py
│   ├── l2_bayesian/
│   │   ├── __init__.py
│   │   ├── optimizer.py
│   │   ├── objective.py
│   │   └── space.py
│   ├── l3_orchestrator.py
│   ├── hmi/
│   │   ├── approval_service.py
│   │   └── dashboard.py
│   ├── audit/
│   │   ├── event_store.py
│   │   ├── audit_log.py
│   │   └── tool_executor.py
│   ├── gateway/
│   │   ├── mqtt_client.py
│   │   ├── lads_client.py
│   │   └── sila_client.py
│   └── plugins/cell_culture/
│       ├── __init__.py
│       ├── environment.py
│       ├── channels.py
│       ├── events.py
│       ├── tools.py
│       ├── sanitizer.py
│       ├── prompt.py
│       ├── confidence.py
│       ├── aggregate_imaging.py
│       └── raman.py（v1.5 以降）
├── sim/plant_model/
│   ├── __init__.py
│   ├── manstein_ode.py
│   └── gp_bias_correction.py（Phase 2）
├── infra/virtual_edge/
│   ├── __init__.py
│   └── dummy_bioreactor.py
├── config/
│   ├── cell_culture_envelope.yaml
│   ├── manstein_recipe.yaml
│   └── mqtt_topics.yaml
└── tests/
    ├── test_plant_model.py
    ├── test_cell_culture_plugin.py
    ├── test_l1_recipe_engine.py
    ├── test_approval_flow.py
    ├── test_audit_log.py
    └── test_bo_reproducibility.py
```

---

## 8. リスクと対応

| # | リスク | 影響 | 対応 |
|---|---|---|---|
| R1 | physical-ai-core の改修が想定以上に大きい | Phase 1 遅延 | Phase 0 で改修方針を確定。必要に応じ L1 エンジンを core 外に実装 |
| R2 | Manstein ODE が実データと乖離 | plant_model 信頼性低下 | 原典に忠実に実装しつつ、細胞株毎の再校正フックを設計 |
| R3 | Raman 校正が iPSC で難航 | Phase 2 遅延 | v1.5 で十分なデータ取得。Nova FLEX2 を正解ラベルとして維持 |
| R4 | 研究者の承認応答が遅い | 制御サイクル停止 | タイムアウト時は安全側デフォルト。HMI 通知を強化 |
| R5 | Annex 22 最終文本が予想と異なる | 規制対応設計の見直し | R&D 一次なので柔軟に対応。動向を継続監視 |
| R6 | BO 目的関数の重みが決まらない | L2 実装遅延 | Phase 0 で合意を必須とする。暫定重みで開始 |

---

## 9. 次のアクション

1. **Phase 0 未決事項の解消**: BO 目的関数重み、承認タイムアウト、DSL 文法、core 改修方針
2. **Phase 1 実装開始**: `sim/plant_model` の Manstein ODE と `cell_culture` plugin から着手
3. **テスト駆動**: plant_model golden test と L1 イベント網羅テストを先に作成
4. **段階的レビュー**: 各モジュール完成時に設計文書との整合レビュー

---

## 10. 参照

- `docs/design/closed_loop_planning/03_swarm_findings_integration.md`
- `docs/design/closed_loop_planning/05_implementation_plan_phase1.md`
- `docs/design/adr/0001-control-architecture.md`
- `docs/design/kg_to_auto_cell.md`
- `docs/design/roadmap.md`
- `docs/design/requirements.md`
