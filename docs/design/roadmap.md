# auto_cell A 層 技術ロードマップ

> **Scope**: iPSC 浮遊/凝集体バイオリアクター制御（A 層）
> **前提**: ADR-0001、`kg_to_auto_cell.md`、設計再検討レポート
> **目的**: v1/Phase 2/Phase 3 の機能分割と、フェーズ間移行条件を数値化する。

本ロードマップは「固定検証済設定点先行 → シミュレーション検証 → 実 run 蓄積 → 適応制御」という漸進的アプローチを採る。各フェーズの移行は**数値条件**を満たすことで判断する。〔設計判断〕

---

## 1. フェーズ概要

| フェーズ | 時期（目安） | 主要テーマ | run 蓄積目安 |
|---|---|---|---|
| **v1 / Phase 1** | 0–6 ヶ月 | L1 決定的ルール、Manstein ODE、Nova FLEX2、at-line 凝集体画像、ALCOA-lite、HITL | 10+ run（基線確立） |
| **Phase 2** | 6–18 ヶ月 | MPC シミュレーション、Raman アドバイザリ、画像定量化、静的決定論的 AI 統制 | 30+ run |
| **Phase 3** | 18–36 ヶ月 | 多変数適応 MPC、Raman 閉ループ、DL 品質代理指標、GMP IQ/OQ/PQ 移行 | 50–100+ run |

> run 蓄積数は同一プロトコル・同一細胞株系での実施を想定。細胞株変更時は累積ではなく「関連 run 数」で再評価。〔設計判断〕

---

## 2. v1 / Phase 1：決定的制御コア

### 2.1 機能一覧

| # | 機能 | 内容 | 実装場所 | 完了基準 |
|---|---|---|---|---|
| 1 | **L1 決定的レシピ/ルールエンジン** | Manstein プロトコル（灌流 0→7 vvd、固定設定点、条件起動給餌）を state machine で実行 | `src/auto_cell/plugins/cell_culture/` | 全イベントに対する決定的応答を単体テストで網羅 |
| 2 | **Manstein ODE plant_model** | Tier2 検証リグ。6 項 Monod 型 ODE | `sim/plant_model/` | 7 日 35×10⁶ cells/mL 軌道を CI で再現 |
| 3 | **Nova FLEX2 at-line 分析** | glucose/lactate/glutamine/osmolality/viability 等の at-line 計測 | `gateway`/LADS/SiLA2 adapter | 4.5 min 以内でデータ取得し event_store へ |
| 4 | **at-line 凝集体画像** | brightfield/FlowCam 等で凝集体径（平均径・大径割合）を取得 | `route_channel`（analog channel 経由） | 日次 cadence で L1 イベント発火 |
| 5 | **ALCOA-lite 監査ログ** | 全操作・副作用ツール呼び出しを不変ログ化 | `event_store`, `tool_executor` | 誰/いつ/何を/なぜ が追跡可能 |
| 6 | **Human-on-the-loop 承認** | 包絡線外 setpoint・trigger_passage・BO 提案は研究者承認 | HMI + approval workflow | 承認・拒否・タイムアウトのログを残す |
| 7 | **Raman 校正計画（v1 観測）** | in-line Raman を設置・記録。Nova FLEX2 を正解ラベル | device layer | 1+ バッチでデータ取得開始 |

### 2.2 移行条件（Phase 1 → Phase 2）

以下を**すべて**満たすこと。〔設計判断〕

| # | 条件 | 数値基準 |
|---|---|---|
| 1 | 同一プロトコルでの run 蓄積 | **10+ run** |
| 2 | Manstein 軌道再現性 | Tier2 plant_model CI 成功、実 run で VCD トレンドが定性的一致 |
| 3 | L1 決定性検証 | 全イベント応答の単体テスト pass、state machine 入力→出力対応表完成 |
| 4 | ALCOA-lite 運用 | 全副作用ツールの監査ログ取得を 3+ run で確認 |
| 5 | HITL 承認フロー | 承認・拒否・タイムアウトの各パスを PoC 完了 |
| 6 | Raman データ取得 | 1+ バッチで in-line Raman スペクトル＋Nova 正解ラベルを取得 |

---

## 3. Phase 2：シミュレーションとアドバイザリ

### 3.1 機能一覧

| # | 機能 | 内容 | 前提 / 入力 | 完了基準 |
|---|---|---|---|---|
| 1 | **MPC シミュレーション** | plant_model 上で perfusion rate を操作変数とする MPC を試行 | `mpc_roadmap_l1`, `mpc_ipsc_perfusion` | シミュレーションで乳酸/osmolality 抑制を確認 |
| 2 | **Raman アドバイザリ（v1.5）** | glucose/lactate 推定値を HMI 表示。L1 フィードバックは**手動承認** | 5+ バッチ校正データ | RMSEP < 15%（暫定、用途により再協議） |
| 3 | **凝集体画像定量化** | 平均径に加え **大径凝集体割合（>400 µm）**、円形度等を自動算出 | at-line 画像データ | 日次レポートと L1 早期警戒イベント |
| 4 | **静的決定論的 AI 統制** | L2 BO の reproducibility test、モデルカード、checksum | `static_deterministic_proof` | CI で同じ train → 同じ提案を確認 |
| 5 | **信頼度スコア層（v1）** | BO GP 事後分散から信頼度を計算し HMI 表示 | `confidence_score` | 低信頼度提案を HITL へエスカレーション |
| 6 | **at-line 品質代理指標の調査** | 凝集体画像からの未分化/自発分化推定、rapid micro/ATP 無菌検知 | `add_aggimg_aggregate_quality_proxy` | 調査レポートと PoC 計画 |
| 7 | **BO 目的関数の具体化** | 収量×生存率×多能性マーカー×凝集体適正サイズ×コストの重み確定 | 研究者合意 | 目的関数をコード化し 1+ run で試行 |

### 3.2 移行条件（Phase 2 → Phase 3）

以下を**すべて**満たすこと。〔設計判断〕

| # | 条件 | 数値基準 |
|---|---|---|
| 1 | run 蓄積 | **30+ run**（同一プロトコル・細胞株系） |
| 2 | MPC シミュレーション | plant_model 上で 7 日間の制約充足率 > 95% |
| 3 | Raman 校正 | **5+ バッチ**で PLS モデル構築。予測誤差が用途許容範囲内 |
| 4 | 画像定量化 | 平均径・大径割合の at-line 自動計測を 5+ run で運用 |
| 5 | 静的決定論的証明 | L2 BO の再現性テストを CI 化。モデルカードを全バージョンで作成 |
| 6 | 信頼度スコア | 低信頼度エスカレーションの感度分析を実施 |
| 7 | BO 目的関数 | 研究者合意済みの重みで 3+ run の最適化試行 |

---

## 4. Phase 3：適応制御と GMP 移行

### 4.1 機能一覧

| # | 機能 | 内容 | 前提 / 入力 | 完了基準 |
|---|---|---|---|---|
| 1 | **多変数適応 MPC** | perfusion rate・撹拌・DO setpoint 等を多変数で最適化 | 50–100+ run データ、MPC シミュレーション成功 | 実 run で目標軌道の追従誤差 < 10% |
| 2 | **Raman 閉ループ（v2）** | glucose/lactate 推定値を L1 フィードバックへ自動反映 | v1.5 アドバイザリで性能確認、drift 監視構築 | 24 h 連続運転で drift 検知可能 |
| 3 | **DL 品質代理指標** | 凝集体画像 DL で未分化/自発分化を推定 | 30+ run の画像＋offline QC ラベル | AUC > 0.8（暫定、細胞株により再協議） |
| 4 | **Hybrid ODE+NN / PINN** | plant_model を Hybrid ODE+NN または PINN へ拡張 | `hybrid_ode_nn`, `pinn`, `digital_twin` | sim/real gap が 20% 以内に縮小 |
| 5 | **多忠実度 BO** | Tier2 plant_model（低忠実度）＋実 run（高忠実度）を組み合わせた BO | `multi_fidelity`, `multifidelity_pinn` | 実 run 数を半減しつつ同程度の最適化性能 |
| 6 | **GMP IQ/OQ/PQ 移行** | 電子署名・完全職員独立性・WORM・IQ/OQ/PQ | `part11`, `esignature`, `staff_independence` | 品質保証部門承認 |

### 4.2 Phase 3 の終了条件（運用移行）

| # | 条件 | 数値基準 |
|---|---|---|
| 1 | run 蓄積 | **50–100+ run** |
| 2 | 適応 MPC | 3+ 細胞株系で追従性能確認 |
| 3 | Raman 閉ループ | 5+ run で drift 未検知、または drift 検知時に安全側 fallback |
| 4 | DL 品質代理指標 | offline QC との一致率が目的に応じて許容 |
| 5 | 規制 | Annex 22 / GMP 対応の技術的統制を文書化・運用開始 |

---

## 5. 将来技術の位置づけ（ADR-0001 §9 対応）

| 技術 | 導入フェーズ | 層 | 用途 | HITL |
|---|---|---|---|---|
| MPC | Phase 2 シミュレーション → Phase 3 実装 | L1 拡張 | perfusion rate 等の制約付き最適化 | Phase 3 実 run 導入時は承認必須 |
| PINN / Digital Twin | Phase 2 調査 → Phase 3 実装 | Tier2 plant_model / L2 BO 低忠実度モデル | sim/real gap 縮小、多忠実度 BO | モデル更新時は承認必須 |
| Hybrid ODE+NN | Phase 3 | plant_model 拡張 | 物理法則＋データ駆動のハイブリッド | モデル更新時は承認必須 |
| 信頼度スコア層 | Phase 2 → 継続 | L2/L3 と HMI の間 | 低信頼度 AI 出力のエスカレーション | 低信頼度時は自動エスカレーション |

> **MPC の根拠**: CHO fed-batch で抗体タイトル 2% 向上等の実用化報告あり。iPSC 灌流でも perfusion rate の制約付き最適化に有効な可能性がある〔`mpc_ipsc_perfusion`, `mpc_lactate_feedback`; 推定〕。〔`alignment_with_downloaded_report.md` §5.1-1〕

---

## 6. 未解決事項と次のステップ

| # | 未解決事項 | 影響 | 次のステップ | 目標時期 |
|---|---|---|---|---|
| U1 | BO 目的関数の重み（収量 vs 多能性 vs コスト） | L2 最適化方向性 | 研究者ヒアリング | Phase 1 終了前 |
| U2 | 承認タイムアウト値の運用最適化 | HMI/ワークフロー | 感度分析 | Phase 1 中 |
| U3 | iPSC-native ammonia threshold | L1 イベント化の可否 | 文献サーチ or 実験決定 | Phase 1 中 |
| U4 | Raman 細胞散乱補正の定量式 | Raman 推定精度 | 標準添加/混合標準実験 | Phase 2 中 |
| U5 | DL 品質代理指標の検証 | Phase 3 移行 | 画像＋QC ラベル蓄積 | Phase 2 中 |
| U6 | Annex 22 最終文本・施行日 | GMP 移行計画 | 規制動向モニタリング | 継続 |

---

## 7. トレーサビリティ

| 設計要素 | KG ノード |
|---|---|
| MPC ロードマップ | `mpc`, `mpc_ipsc_perfusion`, `mpc_roadmap_l1`, `mpc_lactate_feedback` |
| PINN/DT/Hybrid ODE+NN | `pinn`, `digital_twin`, `hybrid_ode_nn`, `multifidelity_pinn` |
| Raman 校正 | `raman_calibration_ipsc`, `raman_pls_model`, `raman_confidence_score` |
| 凝集体画像品質代理指標 | `add_aggimg_aggregate_quality_proxy`, `add_aggimg_aggregate_size_pluripotency` |
| 静的決定論的統制 | `static_deterministic_proof`, `static_model`, `deterministic_output` |
| 信頼度スコア | `confidence_score`, `prediction_confidence_score` |
| ドリフト監視 | `drift_monitoring` |
| ALCOA+/CSV/Part11 | `alcoa`, `csv`, `part11`, `audit`, `ebr` |

---

## 出典・参照

| ID | タイトル | パス/URL |
|---|---|---|
| ADR-0001 | Control architecture | `docs/design/adr/0001-control-architecture.md` |
| kg_bridge | KG → auto_cell 設計ブリッジ | `docs/design/kg_to_auto_cell.md` |
| reconsideration | 設計再検討レポート | `docs/design/design_reconsideration_report.md` |
| regulatory_controls | 規制技術統制 | `docs/design/regulatory_technical_controls.md` |
| Manstein 2021 | Manstein & Zweigerdt 2021 | DOI 10.1002/sctm.20-0453; PMC8666714 |
| Borys 2021 | Borys et al. 2021, Stem Cell Res Ther 12:55 | PMC7805206 |

---

*本ロードマップは A 層（iPSC 浮遊/凝集体バイオリアクター制御）に限定。全数値基準は初期仮説であり、実データに基づく再校正が必須。CHO 由来の数値・戦略を iPSC にそのまま転用しない。*
