# 追加作業メモ

## 作成経緯

`/home/sin/Downloads/report/report.md`（フィジカルAI包括調査レポート）と auto_cell A 層設計の照合分析 `docs/design/alignment_with_downloaded_report.md` に基づき、**相違・補完ドメイン**について詳細調査を行い、Knowledge Graph v2 へ追加する。

## 追加調査ドメイン

### 1. iPSC 浮遊灌流における MPC の適用

**背景**: レポートは CHO fed-batch での MPC 実用化を強調。auto_cell A 層では L1 = 決定的レシピ/ルールエンジン。

**調査観点**:
- iPSC 浮遊灌流プロセスにおける MPC の適用例（文献・ベンダ実装）
- 灌流率を操作変数とする多変数制約最適化の可否
- MPC とルールエンジンの比較（実装コスト、検証性、性能）
- auto_cell L1 への導入フェーズ（将来拡張路線図）

**期待成果**:
- 調査レポート: `docs/design/ground_knowledge/additional_mpc_for_ipsc.md`
- KG 差分: `docs/knowledge_graph/generated/additional_mpc_kg_diff.json`

---

### 2. PINN / デジタルツインの iPSC 培養への適用

**背景**: レポートは PINN ベースハイブリッド DT を Phase 2 で推奨。auto_cell plant_model は Manstein ODE ベース。

**調査観点**:
- iPSC 培養における PINN/ハイブリッドモデルの事例
- データ要件（50-100 バッチ）と R&D 一次の整合性
- plant_model（ODE）から PINN への拡張路線
- 不確実性定量化（95% 信頼区間）の実装方法
- 多忠実度 BO との連携

**期待成果**:
- 調査レポート: `docs/design/ground_knowledge/additional_pinn_dt_for_ipsc.md`
- KG 差分: `docs/knowledge_graph/generated/additional_pinn_dt_kg_diff.json`

---

### 3. iPSC 浮遊培養での Raman 校正戦略

**背景**: レポートは Raman を TRL 8-9 と評価。auto_cell は iPSC 実証の少なさを留保。

**調査観点**:
- iPSC 浮遊/凝集体培養における Raman 適用事例
- capacitance/Raman/Nova FLEX2 の組み合わせ校正戦略
- 凝集体・細胞密度による光散乱の影響
- PLS モデル構築に必要なバッチ数・校正設計
- CHO 由来モデルから iPSC への転移可能性

**期待成果**:
- 調査レポート: `docs/design/ground_knowledge/additional_raman_calibration_ipsc.md`
- KG 差分: `docs/knowledge_graph/generated/additional_raman_kg_diff.json`

---

### 4. CHO から iPSC への CPP 転換・相違

**背景**: レポートは CHO/mAb 事例中心。auto_cell は iPSC 浮遊灌流。

**調査観点**:
- CHO と iPSC の代謝特性の違い（グルコース消費、乳酸生成、アンモニア、グルタミン）
- 凝集体形成が CPP に与える影響（撹拌、シア、酸素拡散）
- mAb タイトル vs 未分化/多能性品質マーカーの目的関数の違い
- CHO の最適化成果を iPSC に転用する際の注意点

**期待成果**:
- 調査レポート: `docs/design/ground_knowledge/additional_cho_to_ipsc_cpp.md`
- KG 差分: `docs/knowledge_graph/generated/additional_cho_ipsc_kg_diff.json`

---

### 5. PIC/S Annex 22 対応ロードマップ

**背景**: レポートは full GMP/Annex 22 準拠を見据える。auto_cell は R&D 一次。

**調査観点**:
- Annex 22 の「Critical AI」定義と細胞培養制御の対応
- R&D 一次で導入可能な技術的統制（ALCOA-lite、監査ログ、XAI、信頼度スコア）
- 静的・決定論的モデルの証明方法
- 電子署名・職員独立性・データ分離の導入段階
- GAMP5 AI Guide との関係

**期待成果**:
- 調査レポート: `docs/design/ground_knowledge/additional_annex22_roadmap.md`
- KG 差分: `docs/knowledge_graph/generated/additional_annex22_kg_diff.json`

---

### 6. 浮遊凝集体画像解析（2D confluency からの転換）

**背景**: レポートは 2D confluency/位相差中心。auto_cell は浮遊凝集体。

**調査観点**:
- 浮遊凝集体の at-line/in-line 画像解析技術（DHM、FBRM、FlowCam）
- 凝集体径・形態からの品質推定（未分化/自発分化）
- label-free DL による品質代理指標の信頼性
- 2D 画像解析技術の凝集体解析への転移可能性

**期待成果**:
- 調査レポート: `docs/design/ground_knowledge/additional_aggregate_imaging.md`
- KG 差分: `docs/knowledge_graph/generated/additional_aggregate_imaging_kg_diff.json`

---

## 統合タスク

各調査完了後、`agent_integrator` + `agent_kg_merge` で以下を作成。

- 統合調査レポート: `docs/design/ground_knowledge/additional_investigation_integrated.md`
- 統合 KG 差分: `docs/knowledge_graph/generated/additional_investigation_diff.json`
- 更新 KG v2.1:
  - `docs/knowledge_graph/knowledge_graph_v2_1.json`
  - `docs/knowledge_graph/knowledge_graph_v2_1.jsonl`
  - `docs/knowledge_graph/knowledge_graph_v2_1.ttl`
  - `docs/knowledge_graph/nodes_v2_1.csv`
  - `docs/knowledge_graph/edges_v2_1.csv`
  - `docs/knowledge_graph/sources_v2_1.csv`
  - `docs/knowledge_graph/ips_automation_knowledge_map_v2_1.html`

## 完了済み追加調査

以下の 6 つの追加調査は完了し、成果物が `docs/design/ground_knowledge/` および `docs/knowledge_graph/generated/` に統合された。〔事実：設計再検討レポート §5.3 C10〕

| # | 調査ドメイン | 成果物レポート | KG 差分 |
|---|---|---|---|
| 1 | iPSC 浮遊灌流における MPC の適用 | `docs/design/ground_knowledge/additional_mpc_for_ipsc.md` | `docs/knowledge_graph/generated/additional_mpc_kg_diff.json` |
| 2 | PINN / デジタルツインの iPSC 培養への適用 | `docs/design/ground_knowledge/additional_pinn_dt_for_ipsc.md` | `docs/knowledge_graph/generated/additional_pinn_dt_kg_diff.json` |
| 3 | iPSC 浮遊培養での Raman 校正戦略 | `docs/design/ground_knowledge/additional_raman_calibration_ipsc.md` | `docs/knowledge_graph/generated/additional_raman_kg_diff.json` |
| 4 | CHO から iPSC への CPP 転換・相違 | `docs/design/ground_knowledge/additional_cho_to_ipsc_cpp.md` | `docs/knowledge_graph/generated/additional_cho_ipsc_kg_diff.json` |
| 5 | PIC/S Annex 22 対応ロードマップ | `docs/design/ground_knowledge/additional_annex22_roadmap.md` | `docs/knowledge_graph/generated/additional_annex22_kg_diff.json` |
| 6 | 浮遊凝集体画像解析（2D confluency からの転換） | `docs/design/ground_knowledge/additional_aggregate_imaging.md` | `docs/knowledge_graph/generated/additional_aggregate_imaging_kg_diff.json` |

統合成果物:

- `docs/design/ground_knowledge/additional_investigation_integrated.md`
- `docs/knowledge_graph/generated/additional_investigation_diff.json`
- `docs/knowledge_graph/knowledge_graph_v2_1.json`（および .jsonl/.ttl/CSV/.html）

## 未解決事項

以下は引き続き解決が必要。〔設計再検討レポート §5.3 C10〕

| # | 未解決事項 | 影響 | 次のステップ |
|---|---|---|---|
| U1 | **iPSC-native ammonia threshold** | L1 イベント化の可否 | 文献サーチ or 実験決定 |
| U2 | **Raman cell-scattering correction quantitative formula** | Raman 推定精度 | 標準添加/混合標準実験 |
| U3 | **DL quality proxy validation** | Phase 3 凝集体画像品質代理指標の信頼性 | 画像＋offline QC ラベル蓄積 |
| U4 | **Approval timeout optimization** | HMI/ワークフロー操作性 | 感度分析 |

## 品質ゲート

- 全主張に出典（DOI/PMID/PMCID/URL）を付与
- 事実/推定/未確定を明記
- A 層スコープ（iPSC 浮遊/凝集体バイオリアクター制御）を遵守
- 既存 KG ノード ID と整合
- CHO 由来の数値を iPSC にそのまま転用しない
