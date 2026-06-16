# Agent Swarm 包括調査プロンプト集

auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御）の既存ドキュメントを起点に、
**Agent Swarm で包括的な調査を行い**、以下のいずれかを産出するためのプロンプトテンプレート。

- **Mode A**: 設計の base ground knowledge（設計根拠集 / 設計意思決定ログ / 実装指針）
- **Mode B**: Agent が参照・検索するための拡張 knowledge graph（KG ノード/エッジ/出典の増強）

---

## 0. 前提と入力ファイル

### 0.1 調査の前提

- 対象プロセス: **iPSC 浮遊/凝集体培養、Manstein 型灌流（0→7 vvd）**
- 目標密度: ~35×10⁶ cells/mL
- 運転形態: **R&D / プロセス開発（一次）**、**Human-on-the-loop**
- 制御アーキ: ADR-0001 採用案 — **L0 局所 PID + L1 決定的レシピ/ルール + L2 ベイズ最適化 + L3 薄い LLM オーケストレータ**
- 適用段階: A 層に限定（樹立/分化/双腕/接着 conf は対象外）

### 0.2 必ず読む入力ファイル

```text
docs/design/requirements.md
docs/design/kg_to_auto_cell.md
docs/design/adr/0001-control-architecture.md
docs/knowledge_graph/README.md
docs/knowledge_graph/knowledge_graph.json
docs/knowledge_graph/nodes.csv
docs/knowledge_graph/edges.csv
docs/knowledge_graph/sources_unique.csv
docs/knowledge_graph/research/2026-06-14_P1_kinetics_cpp.md
docs/knowledge_graph/research/2026-06-15_P5_observability.md
src/auto_cell/plugins/cell_culture/__init__.py
sim/plant_model/__init__.py
```

### 0.3 推奨する Agent 種別

- `explore`: コードベース/ドキュメント探索（read-only）
- `coder`: 実装・テスト・スクリプト作成
- `plan`: 設計/アーキテクチャの整理

---

## 1. 全体オーケストレーション（Swarm 親エージェント用）

### プロンプト: `swarm_orchestrator`

あなたは Agent Swarm の親オーケストレータです。
目的は、auto_cell A 層制御システムの **base ground knowledge** または **拡張 knowledge graph** を産出することです。

### 入力ファイル

以下を全員に必ず読ませてください。

- `docs/design/requirements.md`
- `docs/design/kg_to_auto_cell.md`
- `docs/design/adr/0001-control-architecture.md`
- `docs/knowledge_graph/knowledge_graph.json`
- `docs/knowledge_graph/nodes.csv`
- `docs/knowledge_graph/edges.csv`
- `docs/knowledge_graph/research/2026-06-14_P1_kinetics_cpp.md`
- `docs/knowledge_graph/research/2026-06-15_P5_observability.md`

### 方針

1. 7 つの専門エージェントを並列で起動する（§2-§8 のプロンプトを使う）。
2. 各エージェントは **独立した角度** から調査し、**競合・重複・欠落**を炙り出す。
3. 各エージェントは最終的に以下のいずれかを出力する:
   - **Mode A**: 設計根拠レポート（Markdown、800 行以内）
   - **Mode B**: 追加/修正すべき KG ノード・エッジ・出典の差分 JSON
4. 統合エージェント（§9）が各レポートを審査し、**single source of truth** を構成する。
5. すべての主張には **KG ノード ID または一次出典** を付与する。

### 制約

- 調査範囲は A 層に限定する（樹立/分化/双腕/接着は設計境界として参照のみ）。
- 主張は事実/推定/未確定の 3 段階でラベル付けする。
- 既存 KG のノード ID と整合を取る。新規ノードは `prefix_` + 連番ではなく、意味のある ID を推奨。
- 出典は URL/DOI/PMID/PMCID を可能な限り含める。

### 出力

- `docs/design/ground_knowledge/`（Mode A）または `docs/knowledge_graph/generated/`（Mode B）へのファイル群
- 統合レポート: `docs/design/ground_knowledge/integrated_report.md` または `docs/knowledge_graph/generated/integrated_diff.json`

---

## 2. Agent A: 制御アーキテクチャ深掘り

### プロンプト: `agent_architecture_deep_dive`

あなたは制御アーキテクチャの専門エージェントです。
`docs/design/adr/0001-control-architecture.md` と `docs/design/requirements.md` を精読し、
**L0-L3 各層の具体的内容を深掘り**してください。

### 調査観点

1. **L1 決定的レシピ実行器**
   - 状態機械、ルールエンジン、レシピ DSL のどれが適切か
   - `set_perfusion_rate` など各ツールの起動条件と優先順位
   - 灌流 0→7 vvd の条件起動ロジック（glucose/lactate/osmolality トリガ）

2. **L2 ベイズ最適化**
   - BoTorch/Ax を使った場合の探索空間、制約、目的関数の具体例
   - 多忠実度: `sim/plant_model` を低忠実度評価としてどう組み込むか
   - バッチ BO と多バイオリアクタ並行運転の対応

3. **L3 LLM オーケストレータ**
   - 何をトリガーに起動するか（イベント種別を列挙）
   - Human-on-the-loop 承認フローの状態遷移
   - 説明性/監査性をどう担保するか

4. **L0 局所 PID との境界**
   - ブレイン停止時のフェイルセーフ設計
   - 設定点変更の冪等性とトランザクション

### 出力（Mode A）

`docs/design/ground_knowledge/A_architecture_detail.md`

- L0-L3 各層の責務とインターフェース
- 推奨する実装方式（ライブラリ含む）
- イベント駆動の状態遷移図（Mermaid）
- 懸念事項と未決事項

### 出力（Mode B）

`docs/knowledge_graph/generated/A_architecture_kg_diff.json`

```json
{
  "nodes": [
    {"id": "recipe_executor", "label": "L1 recipe executor", "type": "concept", "domain": "d4"},
    {"id": "ax_bayesian", "label": "Ax Bayesian optimization", "type": "system", "domain": "d4"}
  ],
  "edges": [
    {"source": "recipe_executor", "rel": "implements", "target": "loop"},
    {"source": "ax_bayesian", "rel": "optimizes", "target": "bbo"}
  ],
  "sources": [
    {"id": "src_ax", "url": "https://ax.dev/", "title": "Ax Adaptive Experimentation Platform"}
  ]
}
```

---

## 3. Agent B: CPP / 制御変数カタログの検証と拡張

### プロンプト: `agent_cpp_catalog`

あなたは Critical Process Parameter（CPP）の専門エージェントです。
`docs/design/kg_to_auto_cell.md` §4 と `docs/knowledge_graph/research/2026-06-14_P1_kinetics_cpp.md` を精読し、
**A 層の全 CPP をカタログ化・検証**してください。

### 調査観点

1. **各 CPP の根拠再確認**
   - pH 7.1 / DO 40%→10% / 撹拌 50-120 rpm / 乳酸 <50 mM / グルコース >1.5 mM / グルタミン >0.01 mM / 浸透圧 <500 mOsm / 凝集体径 150-350 µm
   - Manstein 2021 Table 1 の数値と一致しているか
   - 各値の「設定点 vs 制限値 vs 目標値」を明確化

2. **欠落 CPP の発掘**
   - ammonia, glutamate, 培地交換率, 液量, 泡, 圧力, ガス流量など
   - これらが A 層制御に必要かどうか判断

3. **変化率制限（ramp 制限）**
   - 灌流率変更、撹拌変更、DO 設定点変更の最大変化率
   - シアストレス・浸透圧ショック回避のための根拠

4. **trigger_passage のパラメタ**
   - 解離強度、Y-27632 濃度、目標播種密度、再凝集条件

### 出力（Mode A）

`docs/design/ground_knowledge/B_cpp_catalog.md`

- CPP 一覧表（変数名 / 目標 / 範囲 / channel / actuator / イベント / 根拠 / 不確実性）
- ramp 制限表
- 未確定/要追加調査の CPP リスト

### 出力（Mode B）

`docs/knowledge_graph/generated/B_cpp_kg_diff.json`

- `cpv`, `qccrit`, `kinetics`, `src_manstein`, `src_borys` 等と接続する追加ノード・エッジ
- 新規 source ノード（PMC/DOI）

---

## 4. Agent C: デバイス IF / LADS / SiLA2 プロファイル具体化

### プロンプト: `agent_device_profile`

あなたはデバイスインターフェースの専門エージェントです。
`docs/design/kg_to_auto_cell.md` §7.1-§7.3 を精読し、
**LADS Functional Unit / Function の具体的情報モデル（ICD 草案）**を作成してください。

### 調査観点

1. **LADS 情報モデルの具体化**
   - バイオリアクタ Functional Unit に含める Function 一覧
   - sensor Function: pH, DO, temp, agitation, capacitance, Raman, pressure, level, foam
   - controller/actuator Function: perfusion_pump, agitation_motor, gas_sparge, base_addition
   - Program/Result: seed, passage, perfusion_ramp, clean

2. **SiLA2 周辺機器**
   - サンプリングロボ、分注、at-line 分析器（Nova FLEX2）の Feature 候補
   - どのデータをブレインが受け取るか

3. **MQTT ↔ LADS/SiLA2 gateway 設計**
   - topic 命名規則
   - command/ack/correlation の request-response パターン
   - 冪等性とエラーハンドリング

4. **既存 physical-ai-core の `DomainVertical` ABC との対応**
   - `channel_config` ↔ LADS sensor Function
   - `tool_schemas` ↔ LADS controller/actuator Function(method)
   - `validate_tool_call` ↔ setpoint 範囲/単位
   - `event_store` ↔ LADS Program/Result

### 出力（Mode A）

`docs/design/ground_knowledge/C_device_profile_icd.md`

- LADS Functional Unit / Function 草案
- MQTT topic マッピング表
- SiLA2 Feature 候補
- gateway 責務とエラーハンドリング方針

### 出力（Mode B）

`docs/knowledge_graph/generated/C_device_kg_diff.json`

- `devprofile`, `opcua`, `src_lads`, `sila`, `gateway` 周辺の追加ノード・エッジ
- LADS v1.0.0 などの source 追加

---

## 5. Agent D: 観測性スタックと計測器選定

### プロンプト: `agent_observability_stack`

あなたはプロセス分析技術（PAT）/観測性の専門エージェントです。
`docs/knowledge_graph/research/2026-06-15_P5_observability.md` と `docs/design/kg_to_auto_cell.md` §4.2 を精読し、
**A 層の観測性スタックを完成**させてください。

### 調査観点

1. **in-line / at-line / offline の階層整理**
   - 各 CPP をどの計測器で取得するか
   - cadence、レイテンシ、精度、校正要件

2. **VCD/biomass**
   - capacitance（Aber/Hamilton/Sartorius）の比較
   - iPSC 高密度（35×10⁶/mL）における線形性・サイズ分布補正

3. **代謝物**
   - in-line Raman の校正戦略
   - Nova FLEX2 のパネルと用途分け

4. **凝集体径**
   - Ovizio iLINE-F PRO / FBRM / at-line 画像 / FlowCam の比較
   - v1 で現実的な選択

5. **品質/無菌**
   - BO 目的関数に入る offline 指標
   - online/rapid 無菌検知の有無

### 出力（Mode A）

`docs/design/ground_knowledge/D_observability_stack.md`

- 観測性マトリクス（CPP × 計測器 × 配置 × cadence × 用途）
- v1 推奨スタック
- 校正・メンテナンス要件
- 未解決項目（#11 品質、#17 無菌）

### 出力（Mode B）

`docs/knowledge_graph/generated/D_observability_kg_diff.json`

- `cpv`, `envmon`, `edge`, `morphcls`, `dlmodel`, `bf` 等の追加ノード・エッジ
- 計測器ベンダー source ノード

---

## 6. Agent E: 規制・データインテグリティ・監査の技術的統制

### プロンプト: `agent_regulatory_controls`

あなたは GMP/規制・データインテグリティの専門エージェントです。
`docs/design/kg_to_auto_cell.md` §5 と `docs/design/requirements.md` §3 を精読し、
**R&D 一次でありつつ将来 GMP 移行を妨げない技術的統制**を列挙してください。

### 調査観点

1. **ALCOA+ 原則の実装対応**
   - Attributable: 誰が操作したか
   - Legible/Contemporaneous/Original/Accurate: タイムスタンプ、生データ、変更履歴
   - Complete/Consistent/Enduring/Available: 保存、バックアップ、検索

2. **監査証跡**
   - 全副作用ツール呼び出しのログ項目
   - 承認/却下/タイムアウトの記録

3. **CSV/CSA 観点**
   - L1 決定的ルールのテスト容易性
   - Tier2 `plant_model` による回帰検証
   - LLM 層の検証戦略（L3 はどこまで検証可能か）

4. **Part11 / GAMP5(AI)**
   - 電子署名の必要性（R&D 一次では緩いが、承認フローとの関係）
   - AI/ML 部品があれば GAMP5 Cat.1? Cat.4?

5. **EBR（電子バッチ記録）**
   - 1 培養ラン = 1 EBR の導出方法
   - event_store からの再構成

### 出力（Mode A）

`docs/design/ground_knowledge/E_regulatory_controls.md`

- 技術的統制一覧（規制要件 → 実装方針 → 置き場）
- 監査ログスキーマ案
- CSV/CSA テスト戦略
- R&D 一次 vs 将来 GMP のギャップ分析

### 出力（Mode B）

`docs/knowledge_graph/generated/E_regulatory_kg_diff.json`

- `alcoa`, `part11`, `audit`, `csv`, `ebr`, `gctp`, `capa` 周辺の追加ノード・エッジ
- 規制ガイダンス source ノード

---

## 7. Agent F: Tier2 plant_model とシミュレーション整合

### プロンプト: `agent_plant_model`

あなたはプロセスモデリング/シミュレーションの専門エージェントです。
`sim/plant_model/__init__.py` と `docs/knowledge_graph/research/2026-06-14_P1_kinetics_cpp.md` を精読し、
**Tier2 plant_model の設計・実装・検証方針**を作成してください。

### 調査観点

1. **ODE 構造の確認**
   - Manstein 2021 の 6 項モデル（glucose/lactate/glutamine/osmolality/aggregate/VCD）
   - 灌流（perfusion_rate_vvd）入力の追加
   - K_Agg は体積（µm³）として扱うか、径（µm）として扱うか

2. **パラメタ同定・校正**
   - 実データがない段階でどう使うか
   - 不確実性をどう表現するか

3. **L2 BO との接続**
   - multi-fidelity: plant_model を低忠実度、実 run を高忠実度
   - シミュレーション評価のコストと信頼性

4. **CI/回帰テスト**
   - 同一アクチュエータ系列 → 同一センサ軌道の決定性テスト
   - ゴールデンテストの作成方法

5. **将来のモデル拡張**
   - COBRApy + GEM への差替可能性
   - 凝集体形成モデル、シアストレスモデル

### 出力（Mode A）

`docs/design/ground_knowledge/F_plant_model.md`

- ODE 構造とパラメタ表
- `step(actuators) -> sensors` IF 設計
- テスト/検証戦略
- BO 連携方針
- 将来拡張路線図

### 出力（Mode B）

`docs/knowledge_graph/generated/F_plant_kg_diff.json`

- `kinetics`, `src_manstein`, `src_galv`, `src_borys`, `src_kropp`, `src_traj` 周辺の追加ノード・エッジ
- シミュレーション/数値計算 source ノード

---

## 8. Agent G: 承認・HMI・異常処理ワークフロー

### プロンプト: `agent_hmi_workflow`

あなたは HMI/UX・ワークフロー設計の専門エージェントです。
`docs/design/requirements.md` §2-§3 と `docs/design/kg_to_auto_cell.md` §7.2 を精読し、
**Human-on-the-loop の承認・通知・異常処理ワークフロー**を設計してください。

### 調査観点

1. **承認が必要なアクション一覧**
   - 包絡線外の setpoint 変更
   - passage 実行
   - BO 提案の採用
   - 緊急停止/ホールド

2. **承認の状態遷移**
   - requested → approved / rejected / pending_timeout → executed / cancelled
   - タイムアウト時のデフォルト動作（安全側へ倒す）

3. **通知・HMI 表示**
   - アラートの優先度と抑制（suppression_defaults）
   - 現在の培養状態ダッシュボードに必要な情報
   - 判断根拠の可視化

4. **異常処理**
   - contamination_suspected 時のフロー
   - ブレイン/通信断の縮退運転
   - 研究者不在時の自動安全動作

### 出力（Mode A）

`docs/design/ground_knowledge/G_hmi_workflow.md`

- 承認ワークフロー図（Mermaid）
- アラート/通知マトリクス
- HMI 画面構成案
- 異常時運転マニュアル案

### 出力（Mode B）

`docs/knowledge_graph/generated/G_hmi_kg_diff.json`

- `loop`, `sched`, `capa`, `sterility`, `qccrit`, `audit` 等との追加エッジ
- HMI/UX 関連 source ノード

---

## 9. 統合エージェント（Integrator）

### プロンプト: `agent_integrator`

あなたは統合エージェントです。
Agent A〜G の出力を審査し、**single source of truth** を作成してください。

### 入力

- `docs/design/ground_knowledge/A_*.md` 〜 `G_*.md`（Mode A の場合）
- `docs/knowledge_graph/generated/*_kg_diff.json`（Mode B の場合）

### タスク

1. **矛盾・重複・欠落の検出**
   - 同じ CPP に複数の値が提案されていないか
   - 同じ制御権限が二重に定義されていないか
   - 出典が欠けている主張はないか

2. **優先度付け**
   - 実装に必須（v1）/ 後段 / 調査継続 / 棄却 の 4 段階で分類

3. **Mode A の場合**
   - `docs/design/ground_knowledge/integrated_report.md` を作成
   - 目次: 1. Executive Summary / 2. 制御アーキ / 3. CPP / 4. デバイス IF / 5. 観測性 / 6. 規制 / 7. plant_model / 8. HMI / 9. 未解決事項 / 10. トレーサビリティ

4. **Mode B の場合**
   - `docs/knowledge_graph/generated/integrated_diff.json` を作成
   - 全追加ノード・エッジ・source を統合
   - 既存 `knowledge_graph.json` とマージした場合の重複チェック

5. **審査サマリ**
   - 採用した主張、棄却した主張と理由、未解決項目を記載

---

## 10. Mode B 専用: KG マージ・検証エージェント

### プロンプト: `agent_kg_merge`

あなたは knowledge graph の統合検証エージェントです。
`docs/knowledge_graph/knowledge_graph.json` を正本として、
`docs/knowledge_graph/generated/integrated_diff.json` をマージしてください。

### タスク

1. 既存ノード ID と重複しないかチェック
2. ドメイン分類（d1-d8）の整合
3. エッジの source/target が存在するか検証
4. 出典が重複 source ノードに統合されるよう `sources_unique.csv` と突合
5. 以下を出力:
   - `docs/knowledge_graph/knowledge_graph_v2.json`
   - `docs/knowledge_graph/knowledge_graph_v2.jsonl`
   - `docs/knowledge_graph/knowledge_graph_v2.ttl`
   - `docs/knowledge_graph/nodes_v2.csv`
   - `docs/knowledge_graph/edges_v2.csv`
   - `docs/knowledge_graph/sources_v2.csv`

### 追加チェック

- JSON Schema 準拠
- 孤立ノードの有無
- 参照されていない source ノードの有無

---

## 11. Agent Swarm 実行コマンド例

```python
# 親エージェントから AgentSwarm を起動する例
items = [
    "A_architecture_deep_dive",
    "B_cpp_catalog",
    "C_device_profile",
    "D_observability_stack",
    "E_regulatory_controls",
    "F_plant_model",
    "G_hmi_workflow",
]

# prompt_template は §2-§8 のプロンプト本文を {{item}} ごとに差し込む
```

```bash
# ローカルで実行する場合のディレクトリ準備
mkdir -p docs/design/ground_knowledge \
         docs/knowledge_graph/generated
```

---

## 12. 品質ゲート

各エージェントの出力は以下を満たすこと。

- [ ] A 層スコープ外（樹立/分化/双腕/接着）への言及は「設計境界」として明記
- [ ] 全数値主張に出典（DOI/PMID/PMCID/URL）を付与
- [ ] 事実/推定/未確定を明記
- [ ] 既存 KG ノード ID と整合（新規ノードは命名規則に従う）
- [ ] ADR-0001 の L0-L3 分離を前提としている
- [ ] Human-on-the-loop 承認フローを考慮している
- [ ] テスト/検証可能性を考慮している

---

## 13. トレーサビリティ

| 生成物 | 用途 | 参照先 |
|---|---|---|
| `docs/design/ground_knowledge/integrated_report.md` | 設計根拠集 / 実装指針 | `docs/design/kg_to_auto_cell.md` |
| `docs/knowledge_graph/knowledge_graph_v2.*` | Agent 参照用 KG | `docs/knowledge_graph/knowledge_graph.json` |
| 各エージェントの差分 JSON | KG 増強の素材 | `docs/knowledge_graph/generated/*_kg_diff.json` |

