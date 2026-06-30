# Agent Swarm 調査結果統合レポート

> 目的: 6 つの Agent Swarm 調査レポート（S01–S06）の主要発見を統合し、auto_cell A 層の閉ループ実装に影響する設計判断と優先度を整理する。
> Date: 2026-06-30
> 前提: `docs/design/closed_loop_planning/01_roadmap_criticism_verification.md`, `02_missing_assets_for_closed_loop.md`

---

## 1. Executive Summary

Agent Swarm による 6 分野のオンライン調査から、以下の設計判断を導出する。

| # | 判断 | 根拠 | 実装への影響 |
|---|---|---|---|
| 1 | **v1 は決定的 L1 + Manstein ODE + at-line 計測に集中** | MPC/PINN/Raman 閉ループ/DL 代理指標の iPSC 直接実証は未確定 | Phase 1 のスコープを絞り込み、AI/ML は run 間 BO と L3 オーケストレータに限定 |
| 2 | **MPC は Phase 2 シミュレーションから開始し、L1 の上位アドバイザーとして位置づける** | iPSC 浮遊灌流の MPC 実証例は限定的。CHO 実績は iPSC 目的関数に転用不可 | `sim/plant_model` を内部モデルとする do-mpc/CasADi シミュレータを Phase 2 で構築 |
| 3 | **CPP 閾値は Manstein 2021 を基準としつつ、ramp 制限を保守的に再設定** | 現在の ramp 値は文献より急峻。CSPR は 150–500 pL/cell/day の作業範囲 | `validate_tool_call` の ramp 制限を変更。CSPR を監視値として追加 |
| 4 | **アンモニアは監視値のみとし、L1 イベント化は保留** | iPSC ネイティブ閾値が未確定 | `ammonia_high` は参考アラート（P2）として扱い、トリガーにはしない |
| 5 | **Raman は v1 観測→v1.5 アドバイザリ→v2 閉ループ**と段階化 | iPSC 凝集体マトリックスでの光散乱補正が必要。CHO モデル転移不可 | v1 では Nova FLEX2 を正解ラベルとした校正計画。光散乱補正コードを準備 |
| 6 | **PINN/Hybrid ODE+NN は Phase 2 以降。Phase 1 終了後は GP バイアス補正から** | iPSC 直接例なし。30 run 未満では GP バイアス補正が最も現実的 | plant_model の拡張路線を決定 |
| 7 | **凝集体画像は at-line 明視野/位相差を v1 必須とし、Cellpose を推奨** | in-line DHM/FBRM は turn-key iPSC 実証が限定的。DL 代理指標は 2D iPSC で高相関だが浮遊凝集体では未確定 | v1 で analog channel 経由の径取得。Phase 2 で offline 正解ラベル蓄積 |
| 8 | **Annex 22 対応は「9 本柱」で R&D 一次から導入** | 静的・決定論的モデルのみ critical。LLM は非クリティカル限定 | ALCOA-lite、Intended Use、データ分離、職員独立性、静的決定論的証明、XAI、信頼度スコア、ドリフト監視、HITL を v1 から実装 |
| 9 | **信頼度スコア層は GP 事後分散 → PLS Q 残差/Hotelling T² → DL 不確実性 と段階拡張** | 各モデルタイプで信頼度計算方法が異なる | `confidence.py` をモデルタイプ別に設計 |
| 10 | **Human-on-the-loop は全 AI/ML 出力の前提** | Annex 22、安全性、研究者信頼 | 承認ワークフローを v1 から実装 |

---

## 2. 分野別主要発見

### 2.1 S01: MPC for iPSC Perfusion

| 項目 | 発見 | 確度 |
|---|---|---|
| iPSC 浮遊灌流の MPC 直接実証 | 査読付き論文・ベンダー事例ともに限定的 | 事実/未確定 |
| 最も近い事例 | MSC 乳酸ベース DARX-MPC（Van Beylen 2020）; PSC 動的灌流（Huang 2020） | 事実 |
| 実装ライブラリ推奨 | Phase 2: do-mpc + CasADi; Phase 3: acados | 推定 |
| L1 統合 | MPC は「上位 setpoint アドバイザー」。提案は `validate_tool_call` / sanitizer を通過後に実行 | 設計判断 |
| cadence | 30 min〜2 h（Phase 2）。分単位〜15 min（Phase 3）で十分 | 推定 |
| 状態変数 | VCD, viability, glucose, lactate, glutamine, osmolality, aggregate_diameter, DO, pH | 推定 |
| 操作変数 | perfusion rate（将来 glucose/glutamine bolus） | 推定 |
| 制約 | CPP 包絡線（Manstein 2021）、ramp 制限 | 事実/推定 |
| Annex 22 | Critical 用途では静的・決定論的モデルとして扱う | 推定 |

**設計含意**: `sim/plant_model` の Manstein ODE を内部モデルとする MPC シミュレータを Phase 2 で追加。v1 では L1 決定的ルールのまま。

### 2.2 S02: iPSC CPP Thresholds

| 項目 | 発見 | 確度 |
|---|---|---|
| アンモニア閾値 | iPSC 凝集体培養で系統的毒性試験は未確認。hESC では 5 mM まで影響なし（Chen 2010） | 未確定 |
| CSPR | Manstein 2021（7 vvd @ 35e6 → 200 pL/cell/day）と Huang 2020 から **150–500 pL/cell/day** | 推定 |
| 大径凝集体 >400 µm | Borys 2021, Huang 2020 で壊死リスク。Warning >15 % / Limit >20 % | 推定 |
| Ramp 制限 | 現在の値（±0.5 vvd/30 min, ±20 rpm/5 min）は文献より急峻 | 推定 |
| 推奨暫定 ramp | perfusion ±0.25 vvd/h, agitation ±5 rpm/h, DO ±5 %/h, pH ±0.05/h | 推定 |
| シア絶対値 | iPSC 凝集体に対する安全絶対シア応力閾値は未確立 | 未確定 |

**設計含意**: `kg_to_auto_cell.md` の ramp 制限を更新。CSPR を `CellCultureEnv` の計算フィールドとして追加。アンモニアは `ammonia_high` 参考アラートのみ。

### 2.3 S03: Raman Scattering & Calibration

| 項目 | 発見 | 確度 |
|---|---|---|
| iPSC Raman 実証 | 公開文献で turn-key iPSC 浮遊凝集体実証は稀/未確定 | 未確定 |
| 光散乱 | Mie 散乱で Raman 強度減衰。Beer-Lambert 非適合 | 事実 |
| cell-scattering correction | `Log(R_cell) = a × C^b`（Yang 2024）。iPSC パラメータ再推定必要 | 事実/未確定 |
| 前処理 | SNV/MSC/EMSC + Savitzky-Golay 微分が標準 | 事実 |
| 内部標準 | 水ピーク 1600–1700 cm⁻¹（中心 1645 cm⁻¹） | 事実 |
| PLS バッチ数 | 初期 3–5、ロバスト 5–15、転移 10+ | 推定 |
| 共変量 | capacitance VCD、凝集体径を X ブロックへ追加 | 推定 |
| 精度目標 | RMSEP ≤ 操作範囲 10 %、R² ≥ 0.95 | 推定 |

**設計含意**: v1 では Raman データを観測・記録のみ。Nova FLEX2 を正解ラベル。`raman.py` モジュールで前処理・光散乱補正・PLS パイプラインを構築（v1.5 向け）。

### 2.4 S04: PINN / Hybrid DT

| 項目 | 発見 | 確度 |
|---|---|---|
| iPSC 直接例 | 公表文献・産業実装ともに未確認 | 事実 |
| Phase 2 推奨 | GP バイアス補正（<30 run） | 推定 |
| Phase 3 推奨 | Hybrid ODE+NN（50–100 バッチ） | 推定 |
| Phase 4 | PINN/DT（100+ バッチ） | 推定 |
| 推奨構造 | Universal Differential Equation（UDE）型。質量収支保持 + µ/q/f_agg を NN 化 | 推定 |
| フレームワーク | PyTorch + torchdiffeq（Phase 2–3）、DeepXDE（Phase 4 プロトタイプ） | 推定 |
| 不確実性 | Deep Ensemble または GP バイアス補正から開始 | 推定 |
| MPC 統合 | アドバイザリ層に限定。訓練 MV 範囲外で外挿破綻リスク | 推定 |

**設計含意**: `plant_model` は Phase 1 Manstein ODE → Phase 2 GP bias correction → Phase 3 Hybrid ODE+NN と段階拡張。`digital_twin.py` モジュールを Phase 2 から追加。

### 2.5 S05: Aggregate Imaging & DL Proxy

| 項目 | 発見 | 確度 |
|---|---|---|
| v1 現実的画像 | at-line 明視野/位相差 | 事実 |
| in-line DHM/FBRM | iPSC 凝集体 turn-key 実証は限定的 | 推定 |
| 凝集体径と品質 | >300 µm で OCT4 発現低下、>400 µm で壊死リスク | 事実/推定 |
| label-free DL 代理指標 | Akiyoshi 2024（2D hiPSC）で OCT4/NANOG と r≈0.998/0.978。浮遊凝集体は未確定 | 事実/未確定 |
| セグメンテーション | Cellpose が v1 迅速立ち上げに推奨。Mask R-CNN は接触・重なりに強い | 推定 |
| BO 統合 | v1 は L1 イベント入力、Phase 2 以降に品質項として統合 | 設計判断 |

**設計含意**: `aggregate_imaging.py` モジュールで Cellpose ベースセグメンテーションと径分布・形態メトリクスを v1 実装。offline 正解ラベル蓄積を Phase 2 で開始。

### 2.6 S06: Annex 22 / GAMP5 AI

| 項目 | 発見 | 確度 |
|---|---|---|
| Annex 22 | 2025-07-07 草案公開。2026 年最終採用・2027–28 年施行予想 | 事実/推定 |
| Critical 用途 | 静的モデル・決定論的出力・明示的ルールのみ許容 | 事実 |
| 禁止 | 動的モデル・確率的モデル・生成 AI/LLM（Critical 用途） | 事実 |
| L0–L3 分類 | L0/L1 = 決定論的制御器 / L2 BO/GP = 静的モデル扱い / L3 LLM = 非クリティカル限定 | 推定 |
| GAMP5 AI Guide | 2025-07 発刊。Cat.4/5 に該当 | 事実/推定 |
| 9 本柱 | ALCOA-lite、Intended Use、データ分離、職員独立性、静的決定論的証明、XAI、信頼度スコア、ドリフト監視、HITL | 推定 |

**設計含意**: v1 から ALCOA-lite 監査ログ、Intended Use テンプレート、データ分離、職員独立性（軽量版）、静的決定論的証明（固定シード再現性テスト）を実装。L3 LLM は非クリティカル用途に限定し、プロンプトバージョニング＋入出力ログを実装。

---

## 3. 矛盾・重複の検出と解決

| 項目 | 検出された相違 | 統合判断 |
|---|---|---|
| MPC の位置づけ | S01 は Phase 2 シミュレーション推奨。ADR-0001 は将来拡張。 | **Phase 2 シミュレーション、Phase 3 実装**と統一。 |
| CSPR 値 | S02 は 150–500 pL/cell/day。`kg_to_auto_cell.md` は 0.05–0.3 nL/cell/day（=50–300 pL/cell/day）。 | **150–500 pL/cell/day**を暫定作業範囲とし、細胞株・密度で再校正。 |
| Ramp 制限 | S02 は現在値より保守的を推奨。`kg_to_auto_cell.md` は初期仮説。 | **S02 の暫定値を採用**し、実機校正を必須とする。 |
| Raman 閉ループ時期 | ROADMAP.md は長期。roadmap.md は Phase 2 アドバイザリ・Phase 3 閉ループ。S03 は v1.5 アドバイザリ。 | **v1 観測→v1.5 アドバイザリ→Phase 2/3 閉ループ**と段階化。 |
| PINN 導入時期 | ROADMAP.md は長期。S04 は Phase 2 GP バイアス補正、Phase 3 Hybrid。 | **Phase 2 GP バイアス補正、Phase 3 Hybrid ODE+NN、Phase 4 PINN**と統一。 |
| 画像 DL 品質代理指標 | S05 は Phase 2 以降。roadmap.md は Phase 2 調査。 | **Phase 2 調査＋正解ラベル蓄積、Phase 3 BO 統合**とする。 |

---

## 4. 優先度再分類

### 4.1 v1 / Phase 1 で必須（P0）

1. `sim/plant_model` Manstein ODE 実装 + golden test
2. `cell_culture` plugin: environment/channels/events/tools/sanitizer/prompt
3. L1 決定的レシピ/状態機械/ルールエンジン + DSL
4. MQTT topic 契約（telemetry/event/cmd/ack/state/approval/notify/hmi）
5. `infra/virtual_edge` 仮想バイオリアクター
6. 承認ワークフロー + HMI 基本 UI
7. ALCOA-lite 監査ログ + event_store スキーマ
8. `validate_tool_call` + 更新された ramp 制限 + CPP 包絡線
9. at-line 凝集体画像パイプライン（Cellpose ベース）
10. L2 BO 骨格（探索空間・目的関数・Ax/BoTorch ラッパー）
11. L3 LLM オーケストレータ（非クリティカル用途限定）
12. Intended Use テンプレート + モデルカード + 静的決定論的証明

### 4.2 Phase 2（12–24 ヶ月）で追加（P1）

1. MPC シミュレータ（do-mpc + Manstein ODE）
2. Raman 前処理・光散乱補正・PLS パイプライン（アドバイザリ入力）
3. GP バイアス補正（plant_model 拡張）
4. 信頼度スコア層（GP 事後分散、PLS Q 残差）
5. 凝集体画像定量化・形態メトリクス（BO 入力）
6. LADS/OPC-UA/SiLA2 gateway 実装
7. ドリフト監視
8. XAI/feature attribution（BO/Raman）

### 4.3 Phase 3（24–48 ヶ月）で追加（P2）

1. 多変数適応 MPC（perfusion + agitation + DO + bolus）
2. Hybrid ODE+NN デジタルツイン
3. Raman 閉ループ入力（v2）
4. DL 品質代理指標の BO 統合
5. 経済 MPC
6. GMP 移行準備（IQ/OQ/PQ、電子署名、完全職員独立性）

### 4.4 調査継続（P3）

1. iPSC ネイティブアンモニア閾値
2. シア応答の定量式
3. Raman cell-scattering パラメータの iPSC 再推定
4. Hybrid ODE+NN の構造最適化
5. DL 品質代理指標の offline 正解ラベル蓄積
6. Annex 22 最終文本・施行日

---

## 5. 設計判断ログ

| # | 判断 | 根拠 | 影響ファイル |
|---|---|---|---|
| D1 | v1 は決定的コアに集中 | S01–S06 全てが iPSC AI/ML 実証不足を指摘 | `04_implementation_plan_overview.md`, `05_implementation_plan_phase1.md` |
| D2 | MPC/PINN/Raman 閉ループ/DL 代理指標は Phase 2+ | 直接実証例がない、データ要件が大きい | `04_implementation_plan_overview.md` |
| D3 | ramp 制限を S02 暫定値に更新 | 現在値は文献より急峻 | `kg_to_auto_cell.md`（将来更新）、`05_implementation_plan_phase1.md` |
| D4 | CSPR = 150–500 pL/cell/day | Manstein 2021 + Huang 2020 | `environment.py`, `channels.py` |
| D5 | アンモニアは参考アラートのみ | iPSC 閾値未確定 | `events.py` |
| D6 | Raman は v1 観測→v1.5 アドバイザリ→v2 閉ループ | 光散乱補正・校正データが必要 | `raman.py`, `04_implementation_plan_overview.md` |
| D7 | Cellpose を v1 画像セグメンテーションに採用 | 明視野/位相差に汎用性高し | `aggregate_imaging.py` |
| D8 | Annex 22 9 本柱を v1 から軽量実装 | R&D 一次でも将来 GMP 移行を妨げないため | `regulatory_controls.py`, `audit.py` |
| D9 | 信頼度スコア層をモデルタイプ別に設計 | GP/PLS/DL で計算方法が異なる | `confidence.py` |
| D10 | L3 LLM は非クリティカル用途限定 | Annex 22 禁止事項 | `prompt.py`, `llm_orchestrator.py` |

---

## 6. 未解決事項（実装計画で対応）

| # | 未解決事項 | 対応フェーズ | 次のステップ |
|---|---|---|---|
| U1 | BO 目的関数の重み | Phase 1 | 研究者ヒアリング |
| U2 | 承認タイムアウト値の運用最適化 | Phase 1 | 感度分析 |
| U3 | L1 レシピ DSL 正式文法 | Phase 1 | 実装計画で策定 |
| U4 | core cognitive-loop 改修方針 | Phase 1 | physical-ai-core 設計 |
| U5 | capacitance-VCD 高密度線形性 | Phase 1 | 校正実験 |
| U6 | アンモニア iPSC 閾値 | 調査継続 | 文献サーチ or 実験 |
| U7 | online/rapid 無菌検知 | Phase 2 | ベンダー確認 |
| U8 | Raman cell-scattering パラメータ | Phase 1.5 | 標準添加/混合標準実験 |
| U9 | DL 品質代理指標の offline 正解ラベル | Phase 2 | 画像＋QC ラベル蓄積 |
| U10 | Annex 22 最終文本・施行日 | 継続 | 規制動向モニタリング |

---

## 7. 参照

- `docs/design/closed_loop_planning/swarm_reports/S01_mpc_for_ipsc_perfusion.md`
- `docs/design/closed_loop_planning/swarm_reports/S02_ipsc_cpp_thresholds.md`
- `docs/design/closed_loop_planning/swarm_reports/S03_raman_scattering_ipsc.md`
- `docs/design/closed_loop_planning/swarm_reports/S04_pinn_hybrid_dt_ipsc.md`
- `docs/design/closed_loop_planning/swarm_reports/S05_aggregate_imaging_dl_proxy.md`
- `docs/design/closed_loop_planning/swarm_reports/S06_annex22_gamp5_rd.md`
- `docs/design/closed_loop_planning/01_roadmap_criticism_verification.md`
- `docs/design/closed_loop_planning/02_missing_assets_for_closed_loop.md`
