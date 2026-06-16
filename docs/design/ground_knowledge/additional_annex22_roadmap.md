# PIC/S GMP Annex 22 対応ロードマップ（auto_cell A 層追加調査）

> **担当**: PIC/S Annex 22 roadmap Agent  
> **Scope**: iPSC 浮遊/凝集体バイオリアクター制御（A 層）  
> **前提**: ADR-0001（L0 局所 PID + L1 決定的レシピ/ルール + L2 ベイズ最適化 + L3 薄い LLM オーケストレータ）、R&D 一次 / Human-on-the-loop  
> **Date**: 2026-06-16

---

## 1. エグゼクティブサマリー

PIC/S・EU GMP **Annex 22 "Artificial Intelligence"**（2025-07-07 草案公開、2026 年最終採用・2027–2028 年段階施行が業界で見込まれている）〔事実：PIC/S; 推定：施行時期〕は、**患者安全・製品品質・データインテグリティに直接影響するクリティカル用途での AI/ML モデル**に対し、**静的（static）かつ決定論的（deterministic）モデルのみ**を許容し、**動的学習・確率的出力・生成 AI/LLM を禁止**する初の GMP  AI 専用アネックスである。

auto_cell A 層は現在 **R&D 一次**であり、full GMP/Annex 22 準拠はスコープ外だが、将来の GMP 移行を妨げない「Annex 22-ready」な骨格を持つ。ADR-0001 の **L0–L3 分離**は Annex 22 の要求と本質的に整合している。

| 層 | Annex 22 上の位置づけ | 対応方針 |
|---|---|---|
| L0 局所 PID | 既存の決定論的制御器。AI ではない。 | 変更なし。検証済みデバイス IQ/OQ を活用。 |
| L1 決定的レシピ/ルール | クリティカル経路は**明示的ルール・状態機械**で動作。 | 静的・決定論的。Annex 22 適用外に近い。 |
| L2 BO/GP | 同一データ・シード固定で再現可能なアルゴリズム。 | 静的モデルとして扱える。データ分離・バージョン管理を導入。 |
| L3 LLM オーケストレータ | **非クリティカル用途のみ**（HMI/例外/承認仲介/文書化）。 | Human-on-the-loop（HITL）必須。クリティカル制御には絶対に使わない。 |

**本調査の主張**: A 層 v1 はすでに Annex 22 の骨格に適合しやすい。R&D 一次で導入すべき技術的統制は、**ALCOA-lite 監査ログ、意図用途定義、データ分離、信頼度スコア、Human-on-the-loop** の 5 本柱であり、電子署名・職員独立性・完全なデータ分離は GMP 移行段階で段階的に拡張すればよい。

---

## 2. PIC/S GMP Annex 22 の概要

### 2.1 位置づけとタイムライン

- **正式名称**: EudraLex Volume 4 — GMP Annex 22: Artificial Intelligence（草案）〔事実：EC/PIC/S 2025-07-07〕
- **策定主体**: EMA Inspectors' Working Group と PIC/S が共同起草。FDA・MHRA はオブザーバー参加〔事実：PIC/S ニュース〕。
- **公開協議**: 2025-07-07 〜 2025-10-07〔事実：EC consultation page〕
- **最終化・施行**: 2026 年最終採用、2027–2028 年段階的施行が業界レポートで予想される〔推定：industry analysis〕。ただし公式な施行日は未発表。
- **上位文書**: Annex 11（Computerised Systems）、Chapter 4（Documentation）と併用。Annex 22 は AI/ML 特有の追加要求を定める〔事実：Annex 22 1.Scope〕。

### 2.2 適用範囲（Scope）

Annex 22 1.Scope によれば、本アネックスは以下に適用される。

1. **医薬品・原薬製造で使用されるコンピュータ化システム**に組み込まれた AI/ML モデル
2. **クリティカル用途**: 患者安全、製品品質、データインテグリティに直接影響する予測・分類など
3. **静的モデル（static model）**: 使用中又は新データ取り込みにより性能を適応させない凍結モデル
4. **決定論的出力（deterministic output）**: 同一入力に対し同一出力を返すモデル

逆に、以下は**クリティカル GMP 用途では使用不可**と明記されている。

- **動的モデル（dynamic model）**: 継続的・自動的に学習・適応するモデル
- **確率的モデル（probabilistic model）**: 同一入力で出力が変わるモデル
- **生成 AI / LLM**: ChatGPT 等の生成 AI・大規模言語モデル

生成 AI/LLM は**非クリティカル用途**（文書作成、トレーニング支援、傾向分析等）であれば、**適切な資格・訓練を受けた人間による HITL 確認**のもと使用可能〔事実：Annex 22 1.Scope〕。

### 2.3 主要要求事項（Annex 22 章立て対応）

| Annex 22 章 | 要求の要旨 | A 層への含意 |
|---|---|---|
| 1. Scope | クリティカル用途の静的決定論的 AI のみ | L1 ルール、L2 BO/GP は設計で対応可。LLM は非クリティカル限定。 |
| 2. Principles | 関係者（SME、QA、IT、データサイエンティスト）の協力、資格・責任定義、文書化、QRM | 運用 SOP・役割定義が必要。 |
| 3. Intended Use | モデルのタスク、入力データ特性（共通/希少変動）、限界・バイアス、サブグループ、HITL 時のオペレータ責任を文書化・承認 | L2 BO/GP、将来の画像 DL 等で「意図用途文書」を作成。 |
| 4. Acceptance Criteria | 混同行列、感度、特異度、精度、F1 等の指標と、**置き換える工程の性能以上**であること | BO/GP の性能基準、plant_model との整合を定義。 |
| 5. Test Data | 代表性、層別化、十分なサイズ、正解ラベルの検証、前処理の文書化、生成 AI によるデータ生成は推奨されない | iPSC 培養データの train/valid/test 分離が必須。 |
| 6. Test Data Independency | 訓練・検証に使用したデータをテストに使わない。技術的・手続き的管理。物理対象の再利用禁止。**テストデータ閲覧者は訓練・検証に関与不可**（4-eyes 原則） | 研究者/データサイエンティストの職務分離設計。 |
| 7. Test Execution | 事前承認されたテスト計画、fit for intended use、過学習/未学習確認、逸脱の記録・調査 | CI での plant_model 回帰テスト等と連携。 |
| 8. Explainability | 重要な分類・判断に寄与した特徴量を記録。SHAP・LIME・ヒートマップ等。SME レビュー | L2 BO の獲得関数・GP 事後分布、画像 DL 等で XAI 導入。 |
| 9. Confidence | 予測・分類の信頼度スコアをログ化。低信頼度は「undecided」として人間レビューへ | `confidence_score` + 閾値で Human-on-the-loop 承認へ。 |
| 10. Operation | 変更管理、構成管理、性能モニタリング、入力サンプル空間のドリフト監視、HITL レビュー記録 | モデルバージョン固定、ドリフト検知、再検証トリガ。 |

---

## 3. auto_cell A 層の Annex 22 適用マッピング

### 3.1 Critical AI vs Non-critical AI の分類（A 層視点）

**Critical AI（Annex 22 全要求適用）候補**

A 層で「患者安全・品質・データ完全性に直接影響する」制御経路は、原則として **L1 の決定的ルール**で実装される。AI/ML を導入する場合は以下に限定される。

- **in-line Raman による代謝物予測 → 灌流率制御**: 閉ループ入力として使う場合、PLS 等の静的決定論的モデルが該当。
- **凝集体画像 DL → 継代/撹拌判断**: 自発分化・品質判定に使う場合、静的画像分類モデルが該当。
- **BO の獲得関数・GP 予測**: run 間探索の判断材料。静的モデルとして扱えるが、出力が setpoint 提案に直結する場合は準クリティカル。

**Non-critical AI（HITL 必須）候補**

- **L3 LLM オーケストレータ**: 承認要求文書作成、イベント要約、HMI 説明、SOP ドラフト生成。
- **実験レポート・傾向分析の生成 AI 支援**: 非 GMP 判断の文書化。

### 3.2 静的・決定論的モデルの証明方法

Annex 22 が要求する「static + deterministic」を満たすため、A 層で AI/ML モデルを使う場合は以下を実施する。

| 証明項目 | 技術的アプローチ | 備考 |
|---|---|---|
| 凍結パラメータ | トレーニング後に重み・パラメータを固定し、チェックサム（SHA-256 等）でバージョン管理 | 変更時は再検証。 |
| 固定乱数シード | Python/NumPy/PyTorch の乱数シードを固定 | ニューラルネットの場合必須。 |
| 決定論的推論環境 | 同じライブラリバージョン・CUDA バージョン・ハードウェアで実行 | 浮動小数点の非決定性を最小化。 |
| 再現性テスト | 同一入力 → 同一出力を CI/テストセットで検証 | plant_model 回帰テストと同じ考え方。 |
| モデルカード | 意図用途、訓練データ、前処理、評価指標、制限事項を文書化 | Annex 22 3.1/4.1/5.1 に対応。 |

〔事実：Annex 22 1.Scope, 10.Operation; 推定：industry interpretation〕

### 3.3 L0–L3 制御層と Annex 22 の対応

| 層 | 構成要素 | Annex 22 分類 | 技術的統制 |
|---|---|---|---|
| L0 | 局所 PID（温度/pH/DO/撹拌） | AI ではない決定論的制御器 | ベンダ IQ/OQ、設定点凍結 |
| L1 | レシピ DSL/状態機械/ルールエンジン | 明示的ルールによるクリティカル制御 | `validate_tool_call`、包絡線、監査ログ、EBR-like 記録 |
| L2 | Ax/BoTorch バッチ BO + GP | 静的モデルとして扱う（訓練データ固定・シード固定） | データ分離、モデルカード、獲得関数説明、信頼度（GP 事後分散） |
| L3 | 薄い LLM オーケストレータ | **非クリティカルのみ**、HITL | プロンプトバージョニング、入出力ログ、人承認、RAG により承認済み SOP のみ参照 |

**重要**: A 層 v1 では、クリティカル制御経路に AI/ML を導入しない。したがって Annex 22 の厳格な AI 検証要件は、将来の Raman PLS や画像 DL 等に限定される。

---

## 4. R&D 一次で導入可能な技術的統制

### 4.1 ALCOA-lite + 監査ログ

- 全副作用ツール呼び出し（`set_perfusion_rate`、`trigger_passage` 等）を「誰・いつ・何を・なぜ」で構造化ログ化。
- センサ取り込み、承認状態遷移、システム状態変化も含む。
- 失敗/却下/タイムアウトも保存。
- 時刻は NTP 同期 UTC、correlation ID で因果関係を追跡。

これは既存設計（`audit_schema`、`event_store`、`approval_log`）で実装中〔事実：integrated_report §6.2〕。

### 4.2 意図用途（Intended Use）文書化

L2 BO/GP や将来の ML モデルについて、以下を文書化する。

- モデルが自動化/支援する具体的タスク
- 入力データの種類と範囲（iPSC 浮遊灌流の glucose/lactate/VCD/凝集体径等）
- サブグループ（細胞株、培地ロット、反応器スケール等）
- 限界・バイアスの可能性
- 置き換える工程の性能基準

### 4.3 データ分離と職員独立性

Annex 22 6.Test Data Independency を R&D 段階から設計に組み込む。

- **train/validation/test の技術的分離**: バージョン管理リポジトリでアクセス制御。
- **test データの閲覧者は訓練・検証に関与不可**: 小規模 R&D 組織では「4-eyes / dual control」で緩和可能。
- **物理試料の再利用禁止**: 同一画像・同一バッチデータを訓練と最終テストに使わない。

### 4.4 XAI（Explainability）と信頼度スコア

- **L2 BO**: GP 事後分布の平均・分散を可視化。提案値の不確実性が大きい場合は Human-on-the-loop 承認へ。
- **画像 DL（将来）**: SHAP/LIME/Grad-CAM 等で判断根拠を提示。
- **L1 ルール**: ルール ID・適用条件・参照した CPP 値をログに残すことで自明な説明性を確保。

### 4.5 Human-on-the-loop（HITL）

- 包絡線内の定常制御は自律。
- 包絡線外 setpoint 変更、`trigger_passage`、BO 提案採用、低信頼度 AI 出力は研究者承認。
- 承認履歴を append-only で保存。

これは既存の `human_approval`/`approval_workflow` ワークフローで実現〔事実：integrated_report §8〕。

---

## 5. 電子署名・職員独立性・データ分離の導入段階

| 項目 | R&D 一次（v1） | 将来 GMP 移行時 |
|---|---|---|
| 電子署名 | PIN/パスフレーズ + 監査ログ（ALCOA-lite） | 21 CFR Part 11 / Annex 11 完全署名（ID・パスワードの一意リンク、再署名、署名意味付け） |
| 職員独立性 | 研究者/オペレータ/システムの簡易ロール分離 | QA/製造/QC/IT の明確な役割分離、SOP 化 |
| データ分離 | train/test リポジトリ分離、.dual control | 物理的分離、WORM、定期的レビュー SOP |
| 監査証跡 | 構造化ログ + 簡易ハッシュチェーン | WORM ストレージ + 定期レビュー + 完全トレーサビリティ |
| 変更管理 | バージョン管理 + 承認ワークフロー | GAMP IQ/OQ/PQ、影響評価、再検証 SOP |

〔推定：R&D 一次 vs GMP のギャップは integrated_report §6.5 に基づく〕

---

## 6. GAMP5 AI Guide との関係

Annex 22 は **EU/PIC/S の規制ガイダンス**であり、**ISPE GAMP 5 2nd Edition + GAMP Guide: Artificial Intelligence（2025）** は業界標準の検証フレームワークである。両者は競合せず、GAMP5 AI Guide が Annex 22 の実装方法を支える。

- **GAMP5 2nd Ed Appendix D11**: AI/ML ライフサイクル（concept / project / operation）を導入〔事実：ISPE GAMP5〕。
- **GAMP AI Guide（2025）**: データガバナンス、モデルガバナンス、動的システム、リスク管理、検査対応を包括的に扱う〔事実：ISPE GAMP AI Guide〕。
- **A 層への適用例**:
  - L2 BO/GP → GAMP Category 4/5（設定済み製品/カスタムアプリ）として扱う。
  - L3 LLM → GAMP Category 5（カスタム AI）+ 非クリティカル用途限定。
  - データパイプライン → GAMP Category 1/3（インフラ/標準製品）として IQ/OQ を実施。

---

## 7. Annex 22-ready 導入ロードマップ

### Phase 1（0–12 ヶ月）— 基盤構築

1. **AI 使用用途インベントリ作成**: L0–L3 のどこに AI/ML が入るかを列挙し、critical/non-critical に分類。
2. **意図用途文書のドラフト**: L2 BO/GP、将来の Raman PLS/画像 DL 向けテンプレート作成。
3. **ALCOA-lite 監査ログ完成**: 全副作用ツール・承認・イベントを構造化ログ化。
4. **データ分離の設計**: train/valid/test のリポジトリ分離、職員独立性ポリシー（dual control 緩和含む）。
5. **Human-on-the-loop 承認ワークフロー**: 包絡線外アクション・BO 提案・継代トリガの承認を運用開始。

### Phase 2（12–24 ヶ月）— 静的決定論的 AI の導入

1. **Raman PLS 等の閉ループモデル**: 静的・決定論的な chemometric モデルを導入。チェックサム・バージョン固定・再現性テスト。
2. **信頼度スコアの実装**: GP 事後分散・PLS 予測信頼区間を HMI に表示。低信頼度時は承認へ。
3. **XAI の導入**: 画像 DL の場合は SHAP/Grad-CAM、タブラー系は特徴量重要度を記録。
4. **ドリフト監視の設計**: 入力サンプル空間（glucose/lactate 分布、凝集体径分布）の変化を検知し、再校正トリガ。
5. **電子署名の拡張**: R&D から GMP 移行に向けた IdP 選定と署名ワークフロー PoC。

### Phase 3（24–48 ヶ月）— GMP 完全準拠への移行

1. **IQ/OQ/PQ**: L2 AI コンポーネント・データパイプラインに対する完全な資格確認。
2. **性能等価性の実証**: AI/ML モデルが置き換える手動工程の性能以上であることを文書化。
3. **完全な職員独立性**: QA/製造/QC/IT/データサイエンスの役割分離と SOP 化。
4. **継続的モニタリング**: 性能・ドリフト・入力空間の定期レビュー、再検証サイクル。
5. **ベンダー資格**: OPC-UA/LADS デバイス、Raman、画像分析器等の AI 関連部分のサプライヤー監査。

---

## 8. リスク・注意点・未確定事項

| # | 項目 | 確度 | 内容 |
|---|---|---|---|
| U1 | Annex 22 最終文本・施行日 | 未確定 | 2026 年最終採用・2027–28 施行は業界予測。正式な発効日は未発表。 |
| U2 | A 層プロセスが Annex 22 の「製造」に該当するか | 推定 | A 層は R&D/プロセス開発なので、現時点では Annex 22 直接適用外。将来の GMP 製造工程に組み込まれる際に適用。 |
| U3 | BO/GP を「静的決定論的モデル」と見なせるか | 推定 | 訓練データ・シード・ハイパーパラメータ固定で同一出力が得られるなら該当しうる。規制当局の解釈は未確定。 |
| U4 | 低信頼度閾値 | 未確定 | プロセス・モデル毎に検証。一律 95% 等の数値は初期仮説に留める。 |
| U5 | 電子署名方式・IdP | 未確定 | R&D 一次では軽量。GMP 移行時に Part11/Annex11 要件で再選定。 |

---

## 9. 結論・設計への反映

- auto_cell A 層の **ADR-0001（決定論的 L0-L2 + 薄い L3 LLM）** は、PIC/S Annex 22 の「クリティカル用途は静的決定論的モデル、LLM は非クリティカル+HITL」という要求と本質的に整合している。
- R&D 一次では、**ALCOA-lite 監査ログ、意図用途文書、データ分離、XAI/信頼度スコア、Human-on-the-loop** を Phase 1 で導入することで、将来の Annex 22 対応コストを大幅に削減できる。
- 電子署名・職員独立性・完全データ分離は、GMP 移行のタイミングで段階的に拡張すれば十分。
- LLM（L3）は **R&D 時点から非クリティカル用途に限定**し、per-cycle 制御やクリティカル判断に絶対に使わない設計を維持する。

---

## 10. 出典

| ID | タイトル | URL/DOI/PMCID | 確度 |
|---|---|---|---|
| src_pics_annex22_draft | EudraLex Volume 4 — Draft Annex 22: Artificial Intelligence (July 2025) | https://health.ec.europa.eu/document/download/5f38a92d-bb8e-4264-8898-ea076e926db6_en?filename=mp_vol4_chap4_annex22_consultation_guideline_en.pdf | 事実 |
| src_pics_news | PIC/S news — Joint stakeholders consultation on Chapter 4 / Annex 11 / Annex 22 | https://picscheme.org/en/news/joint-stakeholders-consultation-on-the-revision-of-chapter-4 | 事実 |
| src_ec_consult | EC — Stakeholders' Consultation on EudraLex Volume 4 Chapter 4, Annex 11 and new Annex 22 | https://health.ec.europa.eu/consultations/stakeholders-consultation-eudralex-volume-4-good-manufacturing-practice-guidelines-chapter-4-annex_en | 事実 |
| src_eu_ai_act | Regulation (EU) 2024/1689 — Artificial Intelligence Act | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689 | 事実 |
| src_annex11_draft | EudraLex Volume 4 — Draft Annex 11: Computerised Systems (July 2025) | https://health.ec.europa.eu/document/download/40231f18-e564-4043-94de031f813d38b_en?filename=mp_vol4_chap4_annex11_consultation_guideline_en.pdf | 事実 |
| src_part11 | 21 CFR Part 11 — Electronic Records; Electronic Signatures | https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11 | 事実 |
| src_gamp5 | ISPE GAMP 5 Guide: A Risk-Based Approach to Compliant GxP Computerized Systems, 2nd Edition (2022) | https://ispe.org/publications/guidance-documents/gamp-5-guide-2nd-edition | 事実 |
| src_gamp5_ai | ISPE GAMP Guide: Artificial Intelligence (2025) | https://ispe.org/publications/guidance-documents/gamp-guide-artificial-intelligence | 事実 |
| src_fda_csa | FDA — Computer Software Assurance for Production and Quality System Software | https://www.fda.gov/regulatory-information/search-fda-guidance-documents/computer-software-assurance-production-and-quality-system-software | 事実 |
| src_intuitionlabs_annex22 | Industry analysis — EU GMP Annex 22: AI Compliance in Pharma Manufacturing | https://intuitionlabs.ai/articles/eu-gmp-annex-22-ai-compliance-pharma | 推定 |
| src_pharmout_annex22 | Industry analysis — Annex 22: The Rise of Artificial Intelligence | https://www.pharmout.net/annex-22-artificial-intelligence/ | 推定 |
| src_merit_annex22 | Industry analysis — EU GMP Annex 22: The New AI Regulatory Standard | https://meritsolutions.com/blog-annex-22-ai-pharma-regulation/ | 推定 |
| src_regask_annex22 | Industry analysis — Decoding the New PIC/S Annex 22 | https://regask.com/ai-gmp-decoding-new-pics-annex-22-regulatory-teams/ | 推定 |
| adr0001 | ADR-0001: Control architecture | docs/design/adr/0001-control-architecture.md | 事実 |
| integrated_report | auto_cell A 層統合設計根拠レポート | docs/design/ground_knowledge/integrated_report.md | 事実 |

---

*本レポートは A 層（iPSC 浮遊/凝集体バイオリアクター制御）の R&D 一次/Annex 22-ready 設計に限定。full GMP 移行時にはプログラム全体の QMS/CSV/規制チームによる詳細評価が必要。*
