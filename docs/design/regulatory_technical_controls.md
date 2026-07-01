# auto_cell A 層 規制技術統制（Annex 22-ready）

> **Scope**: iPSC 浮遊/凝集体バイオリアクター制御（A 層）
> **前提**: ADR-0001（L0–L3 分離）、`requirements.md`（R&D/Human-on-the-loop）、`kg_to_auto_cell.md` §5
> **目的**: R&D 一次でありつつ、将来の PIC/S GMP Annex 22（AI）移行を妨げない「骨格」を実質化する技術的統制を定義する。

本書は**プログラム全体の GMP 準拠**（品質マネジメント、職員訓練、施設・機器 qualification 等）を網羅するものではない。auto_cell ソフトウェアに織り込むべき**技術的統制**に焦点を絞る。〔設計判断〕

---

## 1. 統制の全体像：5 本柱

| 柱 | 対象層 | 目的 | KG ノード |
|---|---|---|---|
| **1. Intended Use & リスク分類** | L2/L3/将来 AI | 何のため・どこまで信頼できるかを文書化 | `annex22`, `critical_ai`, `noncritical_ai` |
| **2. データ分離 & 職員独立性** | L2 BO、将来 ML | 訓練/検証/テスト/運用データの分離と責任分離 | `data_segregation`, `staff_independence`, `test_data_independence` |
| **3. 静的・決定論的証明** | L0/L1、L2 BO | 同じ入力 → 同じ出力を再現可能に示す | `static_model`, `deterministic_output`, `static_deterministic_proof` |
| **4. XAI・信頼度スコア・HITL エスカレーション** | L2/L3 | 低信頼度・異常時は人間承認へ | `xai`, `confidence_score`, `feature_attribution`, `hitl` |
| **5. ドリフト監視 & ライフサイクル** | 全 AI/統計モデル | 運用中の性能劣化・入力分布変化を検知 | `drift_monitoring`, `gamp_ai_lifecycle` |

---

## 2. 1 本柱：Intended Use 文書化テンプレート

### 2.1 適用対象

以下のコンポーネントは、導入時に Intended Use 文書を作成する。〔設計判断〕

| コンポーネント | 用途分類 | 備考 |
|---|---|---|
| L2 BO/GP | **非クリティカルAI / プロセス開発支援** | run 間パラメタ提案。最終 setpoint は `validate_tool_call`＋HITL で承認。 |
| 将来 Raman PLS | **非クリティカルAI（v1.5 アドバイザリ）→ 閉ループ（v2 以降）** | v1 は観測・記録のみ。v1.5 はアドバイザリ。v2 は L1 フィードバックへ。 |
| 将来 凝集体画像 DL | **非クリティカルAI（品質代理指標）** | run 内品質の早期警戒。最終判断は研究者。 |
| L3 LLM | **非クリティカルAI / HMI・例外仲介** | 制御ループ外。提案・説明・承認仲介のみ。 |
| L0/L1 | **決定的制御器**（Annex 22 クリティカルAI 定義に該当しない） | 明示的ルール・検証済 PID。Intended Use は簡易。 |

### 2.2 テンプレート項目

各 Intended Use 文書は以下を含む。〔設計判断：GAMP5 AI Guide / Annex 22 draft より要約〕

1. **目的**: 何を達成するためのコンポーネントか（例：次 run の灌流率プロファイルを提案する）。
2. **適用範囲**: 対象細胞株・培地・装置・プロセスフェーズ。
3. **制約**: 入力範囲、動作包絡線、使用しない条件。
4. **権限**: 自動実行可能か、HITL 承認必須か、完全に読み取り専用か。
5. **性能目標**: 再現性、精度、許容誤差、信頼度閾値。
6. **リスク分類**: クリティカル / 非クリティカル。L3 LLM・L2 BO・将来画像 DL は非クリティカルとする。
7. **トレーニングデータ要件**: 最小 run 数、校正バッチ数、細胞株バリデーション。
8. **監視・再評価**: ドリフト監視指標、再トレーニングトリガ。
9. **責任者**: モデル所有者、検証責任者、運用責任者（職員独立性）。

> **重要**: L3 LLM / 生成 AI は**クリティカル用途に使用しない**。クリティカル用途の定義例：setpoint の最終決定を人間の承認なしで行う、安全インターロックを上書きする、無菌バリアを無効化する。〔設計判断：`annex22 --constrains--> llm_orchestrator`〕

### 3.3 Phase 2 で実装した GMP-ready 統制

| 統制 | 実装 | ファイル |
|---|---|---|
| ユーザー認証・RBAC | bcrypt パスワード/PIN + JWT | `src/auto_cell/auth/` |
| 電子署名 | 承認/却下時に PIN + meaning-of-signature を要求 | `src/auto_cell/hmi/approval_service.py` |
| 職員独立性 | 承認者と要求者が同一の場合は拒否 | `src/auto_cell/hmi/approval_service.py` |
| 承認永続化 | SQLite `approval_requests` テーブル | `src/auto_cell/hmi/approval_store.py` |
| 監査証跡レビュー | `audit_trail_reviewed` 記録 + EBR 反映 | `src/auto_cell/audit/audit_log.py`, `ebr_report.py` |

---

## 3. 2 本柱：データ分離と職員独立性

### 3.1 データ分離（train / valid / test / operational）

| データ区分 | 用途 | 技術的統制 | KG |
|---|---|---|---|
| **train** | モデルパラメータ学習 | run_id で分離。将来は時系列 split（過去 run → 未来 run）。 | `data_segregation` |
| **valid** | ハイパーパラメータ・早期停止 | train と同時期でも別 run。漏洩防止。 | `data_segregation` |
| **test** | 最終性能評価 | **運用後に触れない**。test set は frozen。 | `test_data_independence` |
| **operational** | 運用時の推論入力 | 学習データと明確に区分。推論ログを運用データセットとして保存。 | `data_segregation` |

**R&D 一次の実装方針**〔設計判断〕:
- v1/Phase2 では BO の GP 事後分布は「訓練データ固定」で扱う。run 結果が追加されても、次 run 提案前に**明示的再適合**を行い、バージョンを更新する。
- 将来 ML（Raman PLS、画像 DL）では `train/valid/test` をファイル/データベースレベルで分離。checksum を記録。
- 運用データは `event_store` に不変ログとして保存。学習データへの追加は**審査可能な手続き**で行う。

### 3.2 職員独立性（Staff Independence / Dual Control）

| 役割 | 責任 | dual control / 4-eyes |
|---|---|---|
| モデル開発者 | アルゴリズム実装・訓練 | コードレビュー必須 |
| データ管理者 | train/valid/test 分離・管理 | 別担当者が split を確認 |
| 検証責任者 | 再現性テスト・性能評価 | モデル開発者とは別人 |
| 運用責任者 | 運用投入・ドリフト監視 | 承認権限を持つ別担当者 |
| 承認者（研究者） | HITL 最終承認 | システム提案者と別人 |

**R&D 一次の緩和**〔設計判断〕:
- 完全な 4-eyes は R&D 一次では重荷。初期は「**開発者 ≠ 検証者**」と「**承認者 ≠ システム運用者**」の最低 2 点を満たす。
- Phase 2 では電子署名・職員独立性・承認永続化の骨格を実装した（`src/auto_cell/auth/`, `src/auto_cell/hmi/approval_store.py`）。完全 Part 11 対応は今後の GMP 移行時に拡張する。

---

## 4. 3 本柱：静的・決定論的証明

### 4.1 対象と目標

| 層 | 静的・決定論的であるべきか | 証明方法 | KG |
|---|---|---|---|
| **L0 局所 PID** | はい | ファームウェア checksum、ハードウェア検証 | `l0_local_pid`, `deterministic_output` |
| **L1 レシピ/ルールエンジン** | はい | 固定シード再実行テスト、state machine 単体テスト | `recipe_executor`, `rule_engine`, `deterministic_output` |
| **L2 BO/GP** | **静的モデルとして扱う** | 訓練データ固定・シード固定・再現性テスト | `static_model`, `static_deterministic_proof` |
| **L3 LLM** | 否（非決定的） | 非クリティカル用途＋HITL で補償 | `generative_ai`, `noncritical_ai` |

> **L2 BO の注意**: GP 事後分布は確率的だが、**訓練データ・ハイパーパラメータ・乱数シードを固定**すれば「静的モデル」として再現可能。Annex 22 で「動的モデル」と見なされるかは規制当局の解釈に依存する〔未確定〕。〔`static_deterministic_proof`〕

### 4.2 技術的証明手段

| 手段 | 実装 | 保存物 |
|---|---|---|
| **モデルカード** | モデル名、バージョン、訓練データ run_id、ハイパーパラメータ、 Intended Use、性能指標 | `docs/model_cards/<model_id>_<version>.md` |
| **Checksum / ハッシュ** | 訓練データ、アーティファクト（pickle/onnx）、コードの SHA-256 | `model_registry/<model_id>/checksums.json` |
| **固定シード** | numpy/torch GP 乱数シード固定 | 設定ファイルに `seed` 記録 |
| **再現性テスト** | 同じ train → 同じ test 予測 → checksum 一致を CI で検証 | `tests/regression/test_model_reproducibility.py` |
| **決定性証明書** | L0/L1 state machine の入力→出力対応表 | `docs/verification/l1_determinism_report.md` |

### 4.3 L1 決定性の具体例

`recipe_executor` / `rule_engine` は以下で決定性を担保する〔設計判断〕:
- 状態遷移は**現在状態＋入力＋レシピ**のみに依存（過去履歴は event_store 参照だが、再現時は同じ履歴を与える）。
- 浮動小数点演算は Python 標準（IEEE 754）で固定。必要に応じて Decimal。
- 時間依存アクションは**絶対時刻ではなく培養経過時間**で記述し、再現時に同じ相対時間を与える。
- 乱数を使わない（L1 には乱数を含まない）。

---

## 5. 4 本柱：XAI・信頼度スコア・HITL エスカレーション

### 5.1 信頼度スコア層の位置づけ

信頼度スコア層は **L2/L3 と HMI の間**に配置する。〔設計判断：`prediction_confidence_score`, `confidence_score`〕

```
L2 BO/GP ──提案──┐
L3 LLM ───提案──┼──> 信頼度スコア層 ──> HMI ──> 研究者承認 ──> L1 実行
Raman PLS ──推定─┘         ↑
                    低信頼度 → エスカレーション
```

### 5.2 各コンポーネントの信頼度指標

| コンポーネント | 信頼度指標 | 低信頼度時の対応 | KG |
|---|---|---|---|
| **L2 BO/GP** | GP 事後分散（標準偏差）、獲得関数値の不確実性 | 次 run 提案を保留、追加実験推奨 | `confidence_score` |
| **将来 Raman PLS** | Q 残差、Hotelling T²、予測区間 | v1.5 アドバイザリ表示のみ；v2 閉ループ時は HITL または安全側デフォルト | `raman_confidence_score` |
| **将来 凝集体画像 DL** | 予測不確実性（MC dropout / ensemble 分散）、OOD 検出 | 画像を研究者に提示、自動判断不可 | `add_aggimg_aggregate_quality_proxy` |
| **L3 LLM** | 応答一貫性スコア（self-consistency）、参照文書の有無 | 回答を「不確実」としてマーク、研究者確認 | `llm_orchestrator` |

### 5.3 XAI / Feature Attribution

| 用途 | 手法 | 出力先 | KG |
|---|---|---|---|
| BO 提案の根拠 | GP 獲得関数（EI/UCB）の分解、重要パラメータ順位 | HMI「なぜこの提案か」表示 | `xai`, `feature_attribution` |
| Raman PLS | ローディングベクトル、VIP（Variable Importance in Projection） | モデルカード・HMI | `raman_pls_model` |
| 画像 DL | Grad-CAM / SHAP（画像領域帰属） | 研究者確認画面 | `xai`, `feature_attribution` |

> **注意**: LLM による説明は**人間向け要約**であり、形式的な XAI ではない。クリティカルな判断の根拠は GP/PLS/DL の定量的帰属を用いる。〔設計判断〕

---

## 6. 5 本柱：ドリフト監視

### 6.1 監視対象

| ドリフト種別 | 指標 | 検知方法 | 対応 | KG |
|---|---|---|---|---|
| **入力分布ドリフト** | センサ値・CPP の分布変化 | KL divergence / Wasserstein distance / 統計量（mean/std）閾値 | 警報、モデル再校正検討 | `drift_monitoring` |
| **性能ドリフト** | 予測誤差の増大（RMSEP、R²） | at-line 正解ラベル（Nova FLEX2）との差分トレンド | v1.5 アドバイザリ停止→v2 閉ループ停止 | `raman_calibration_ipsc` |
| **概念ドリフト** | プロセス挙動の構造変化（細胞株変更不要等） | 残差の自己相関、ドメイン専門家判定 | 再トレーニング、モデル廃止 | `drift_monitoring` |

### 6.2 実装方針

- **v1**: 手動トリガの再校正（Nova FLEX2 を正解ラベルとして Raman 校正計画）。
- **Phase 2**: 自動化された drift 検知ダッシュボード（入力分布・Raman 残差・画像 DL 残差）。
- **Phase 3**: 閉ループモデルは drift 超過時に自動的に安全側 setpoint へフォールバック。

---

## 7. L3 LLM の非クリティカル用途限定とプロンプトバージョニング

### 7.1 非クリティカル用途の範囲

L3 LLM は以下に限定する。〔設計判断：`annex22 --constrains--> llm_orchestrator`〕

| 許可される用途 | 禁止される用途 |
|---|---|
| 承認要求の仲介・HMI 表示整形 | setpoint の最終決定（承認なし） |
| 曖昧知覚（画像異常等）の要約・候補提示 | 安全インターロックの上書き |
| 新規例外への対応提案（研究者が承認） | 無菌バリア・緊急停止の無効化 |
| BO 結果・Raman 傾向の自然言語説明 | プロンプトインジェクションを受けた任意コード実行 |
| 研究者対話・ログ要約 | 個人情報・機微データの出力 |

### 7.2 プロンプトバージョニング

| 項目 | 統制 | 保存先 |
|---|---|---|
| システムプロンプト | バージョン管理（Git）。レビュー済みのみ運用。 | `src/auto_cell/plugins/cell_culture/prompts/` |
| few-shot 例 | 固定セット。動的取得は審査ログに記録。 | 同上 |
| モデル名・バージョン | 運用ログに記録 | `event_store` |
| temperature / top_p | 固定（推論の再現性向上）。LLM 層の「静的化」 | 設定ファイル |

> LLM 応答は非決定的だが、**プロンプト・パラメータ・モデルバージョンを固定**し、入出力を監査ログに残すことで、運用再現性を「人間が追跡可能な形」で担保する。〔設計判断〕

---

## 8. 実装マップ（core / プラグイン / gateway）

| 統制 | 実装場所 | 備考 |
|---|---|---|
| Intended Use 文書 | `docs/model_cards/` + `regulatory_technical_controls.md` | モデルカードとしてバージョン管理 |
| データ分離 | `data/` 配下のディレクトリ分離 + checksum | 将来 DMS/LIMS 連携 |
| 職員独立性 | 運用手順書（`docs/sops/`） | R&D 一次では緩和 |
| 静的決定論的証明 | `tests/regression/`, `docs/verification/` | CI で再現性テスト |
| XAI / feature attribution | `src/auto_cell/plugins/cell_culture/xai.py` | Phase 2 実装 |
| 信頼度スコア | `src/auto_cell/plugins/cell_culture/confidence.py` | v1 は BO GP 分散から |
| ドリフト監視 | `src/auto_cell/plugins/cell_culture/drift.py` + HMI dashboard | Phase 2 実装 |
| LLM プロンプトバージョニング | Git + `event_store` | 全 LLM 呼び出しにバージョン記録 |

---

## 9. トレーサビリティ

| 設計要素 | KG ノード |
|---|---|
| Annex 22 制約 | `annex22` |
| クリティカル / 非クリティカル AI | `critical_ai`, `noncritical_ai` |
| 静的モデル / 決定論的出力 | `static_model`, `deterministic_output` |
| 生成 AI / LLM | `generative_ai`, `llm_orchestrator` |
| HITL | `hitl`, `human_approval`, `approval_workflow` |
| XAI | `xai`, `feature_attribution` |
| 信頼度スコア | `confidence_score`, `prediction_confidence_score`, `raman_confidence_score` |
| ドリフト監視 | `drift_monitoring` |
| データ分離 | `data_segregation`, `test_data_independence` |
| 職員独立性 | `staff_independence` |
| 静的決定論的証明 | `static_deterministic_proof` |
| ALCOA+/CSV/Part11/EBR | `alcoa`, `csv`, `part11`, `audit`, `ebr` |

---

## 出典・参照

| ID | タイトル | パス/URL |
|---|---|---|
| ADR-0001 | Control architecture — thin LLM orchestrator over deterministic tools + Bayesian optimization | `docs/design/adr/0001-control-architecture.md` |
| requirements | auto_cell A 層 制御システム 要求仕様 | `docs/design/requirements.md` |
| kg_bridge | KG → auto_cell 設計ブリッジ | `docs/design/kg_to_auto_cell.md` |
| Annex 22 draft | EudraLex Volume 4 — Draft Annex 22: Artificial Intelligence (July 2025) | `src_pics_annex22_draft` |
| GAMP5 AI Guide | GAMP 5 Guide: Records & Data Integrity, Annex 11, AI/ML 関連解釈 | 業界ガイダンス（要最新版確認） |
| Manstein 2021 | Manstein & Zweigerdt 2021, Stem Cells Transl Med / STAR Protocols | DOI 10.1002/sctm.20-0453; PMC8666714 |

---

*本書は A 層（iPSC 浮遊/凝集体バイオリアクター制御）に限定。全主張には事実/推定/未確定/設計判断を付与。CHO 由来の数値・戦略を iPSC にそのまま転用しない。*
