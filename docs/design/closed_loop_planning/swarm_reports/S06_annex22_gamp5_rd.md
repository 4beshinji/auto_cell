# S06: PIC/S Annex 22 / GAMP5 AI Guide / EU AI Act の R&D 軽量適用方針

> **担当**: 製薬規制・GMP/CSV 調査エージェント  
> **Scope**: auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御、Manstein 型灌流 0→7 vvd）  
> **前提**: ADR-0001、requirements.md、`docs/design/kg_to_auto_cell.md` §5、`docs/design/ground_knowledge/additional_annex22_roadmap.md`、同 `additional_investigation_integrated.md` §6  
> **Date**: 2026-06-30

---

## Executive Summary

PIC/S・EU GMP **Annex 22 "Artificial Intelligence"** は **2025-07-07 に草案公開**され、2026 年最終採用・2027–2028 年段階施行が業界で見込まれる初の GMP AI 専用アネックスである〔事実：EC/PIC/S 2025-07-07; 推定：施行時期〕。本アネックスは、**患者安全・製品品質・データインテグリティに直接影響するクリティカル用途**において **静的（static）かつ決定論的（deterministic）な AI/ML モデルのみ**を許容し、**動的学習・確率的出力・生成 AI/LLM を禁止**する。

auto_cell A 層の **ADR-0001（L0 局所 PID + L1 決定的レシピ/ルール + L2 ベイズ最適化 + L3 薄い LLM オーケストレータ）** は、この Annex 22 の骨格と本質的に整合している。R&D 一次で導入すべき技術的統制は、**ALCOA-lite 監査ログ、Intended Use、データ分離、職員独立性、静的決定論的証明、XAI、信頼度スコア、ドリフト監視、Human-on-the-loop** の 9 本柱である。電子署名・WORM・完全な職員独立性は GMP 移行段階で段階的に拡張すれば十分。

本レポートの主張はすべて **〔事実〕 / 〔推定〕 / 〔未確定〕** でラベル付けし、出典を明記する。

---

## 1. Annex 22 / EU AI Act / GAMP5 AI Guide の最新動向

### 1.1 PIC/S GMP Annex 22 最新動向

| 項目 | 内容 | 確度 |
|---|---|---|
| 正式名称 | EudraLex Volume 4 — GMP Annex 22: Artificial Intelligence（草案） | 事実 |
| 公開日 | 2025-07-07 | 事実 |
| 協議期間 | 2025-07-07 〜 2025-10-07 | 事実 |
| 策定主体 | EMA GMDP Inspectors' Working Group + PIC/S 共同起草。FDA・MHRA はオブザーバー参加 | 事実 |
| 最終化・施行 | 2026 年最終採用、2027–2028 年段階的施行が業界で予想 | 推定 |
| 公式施行日 | 未発表 | 未確定 |
| 上位文書 | Annex 11（Computerised Systems）、Chapter 4（Documentation）と併用。Annex 22 は AI/ML 特有の追加要求 | 事実 |

出典:
- EC/PIC/S draft Annex 22: https://health.ec.europa.eu/document/download/5f38a92d-bb8e-4264-8898-ea076e926db6_en?filename=mp_vol4_chap4_annex22_consultation_guideline_en.pdf
- PIC/S news: https://picscheme.org/en/news/joint-stakeholders-consultation-on-the-revision-of-chapter-4
- EC consultation: https://health.ec.europa.eu/consultations/stakeholders-consultation-eudralex-volume-4-good-manufacturing-practice-guidelines-chapter-4-annex_en

### 1.2 Annex 22 の適用範囲と核心要求

Annex 22 1.Scope によれば、本アネックスは以下に適用される〔事実〕：

1. 医薬品・原薬製造で使用されるコンピュータ化システムに組み込まれた AI/ML モデル
2. 患者安全・製品品質・データインテグリティに直接影響する**クリティカル用途**
3. **静的モデル**: 使用中又は新データ取り込みにより性能を適応させない凍結モデル
4. **決定論的出力**: 同一入力に対し同一出力を返すモデル

**クリティカル GMP 用途で使用不可**と明記されているもの〔事実〕：

- **動的モデル**（dynamic model）: 継続的・自動的に学習・適応するモデル
- **確率的モデル**（probabilistic model）: 同一入力で出力が変わるモデル
- **生成 AI / LLM**: ChatGPT 等の生成 AI・大規模言語モデル

生成 AI/LLM は**非クリティカル用途**（文書作成、トレーニング支援、傾向分析等）であれば、**適切な資格・訓練を受けた人間による HITL 確認**のもと使用可能〔事実：Annex 22 1.Scope〕。

Annex 22 の章立てと核心要求:

| 章 | 要求の要旨 | A 層への含意 |
|---|---|---|
| 1. Scope | クリティカル用途の静的決定論的 AI のみ | L1 ルール、L2 BO/GP は設計で対応可。LLM は非クリティカル限定。 |
| 2. Principles | SME・QA・IT・データサイエンティストの協力、資格・責任定義、文書化、QRM | 運用 SOP・役割定義が必要。 |
| 3. Intended Use | モデルのタスク、入力データ特性（共通/希少変動）、限界・バイアス、サブグループ、HITL 時のオペレータ責任を文書化・承認 | L2 BO/GP、将来 Raman PLS/画像 DL 用の「意図用途文書」を作成。 |
| 4. Acceptance Criteria | 混同行列、感度、特異度、精度、F1 等の指標と、**置き換える工程の性能以上**であること | BO/GP の性能基準、plant_model との整合を定義。 |
| 5. Test Data | 代表性、層別化、十分なサイズ、正解ラベルの検証、前処理の文書化、生成 AI によるデータ生成は推奨されない | iPSC 培養データの train/valid/test 分離が必須。 |
| 6. Test Data Independency | 訓練・検証に使用したデータをテストに使わない。技術的・手続き的管理。**テストデータ閲覧者は訓練・検証に関与不可**（4-eyes 原則） | 研究者/データサイエンティストの職務分離設計。 |
| 7. Test Execution | 事前承認されたテスト計画、fit for intended use、過学習/未学習確認、逸脱の記録・調査 | CI での plant_model 回帰テスト等と連携。 |
| 8. Explainability | 重要な分類・判断に寄与した特徴量を記録。SHAP・LIME・ヒートマップ等。SME レビュー | L2 BO の獲得関数・GP 事後分布、画像 DL 等で XAI 導入。 |
| 9. Confidence | 予測・分類の信頼度スコアをログ化。低信頼度は「undecided」として人間レビューへ | `confidence_score` + 閾値で Human-on-the-loop 承認へ。 |
| 10. Operation | 変更管理、構成管理、性能モニタリング、入力サンプル空間のドリフト監視、HITL レビュー記録 | モデルバージョン固定、ドリフト検知、再検証トリガ。 |

### 1.3 EU AI Act との関係

| 項目 | EU AI Act | Annex 22 | 関係 |
|---|---|---|---|
| 性質 | 水平・セクター横断的規制 | 垂直・GMP 特化ガイダンス | 並行適用 |
| 対象 | 全 AI システム | GMP 製造環境の AI/ML モデル | Annex 22 は GMP 製造特化 |
| 高リスク | MDR/IVDR 規制製品又はその安全部品となる AI、Annex III 用途 | 患者安全・品質・データ完全性に直接影響するクリティカル用途 | 製造制御 AI は Annex 22 で追加要求 |
| 研究除外 | Article 2(6)–(8): 科学的研究・開発のみを目的とする AI は除外 | R&D 一次は直接適用外（将来の GMP 製造工程で適用） | A 層 R&D は EU AI Act 高リスク該当しにくい〔推定〕 |
| 施行時期 | 2024/08/01 発効。高リスク AI 義務は 2026/08/02（一般）、2027/12（MDR/IVDR 機器）へ延長の動き | 2027–2028 年施行予想 | 両方とも準備期間あり |

**重要な整理**〔推定〕：
- **A 層は現時点で R&D/プロセス開発**であり、GMP 製造工程ではない。したがって Annex 22 の**直接適用外**である。
- ただし、将来の GMP 移行を見据えた「Annex 22-ready」な骨格を R&D 段階から持つことで、移行コストを大幅に削減できる。
- EU AI Act も、科学的研究・開発のみを目的とする内部 R&D ツールは **Article 2(6)–(8) で除外**される可能性が高い〔推定〕。
- Annex 22 と EU AI Act は競合せず、**Annex 22 は GMP 製造という垂直領域で EU AI Act を補完・具体化**する。

出典:
- EU AI Act: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689
- Nature npj Digital Medicine: https://www.nature.com/articles/s41746-024-01232-3
- RAPS AI Act classification guidelines: https://www.raps.org/resource/eu-commission-drafts-guidelines-on-classifying-high-risk-systems-under-the-ai-act.html

### 1.4 ISPE GAMP5 AI Guide（2025）の位置づけ

| 項目 | 内容 | 確度 |
|---|---|---|
| 正式名称 | ISPE GAMP® Guide: Artificial Intelligence | 事実 |
| 発刊 | 2025-07 | 事実 |
| ページ数 | 約 290 ページ | 事実 |
| 関係文書 | GAMP 5 Second Edition（2022）Appendix D11 と併用 | 事実 |
| 性格 | 業界ガイダンス（規制文書ではない） | 事実 |

GAMP 5 Second Edition と AI Guide の分担〔事実〕：

| 文書 | 管轄 |
|---|---|
| GAMP 5 2nd Ed | リスクベースバリデーション哲学、ソフトウェアカテゴリ分類（Cat.1/3/4/5）、V モデルライフサイクル、Part 11/Annex 11 整合 |
| GAMP AI Guide | AI ライフサイクル（concept / project / operation / retirement）、データガバナンス、モデルガバナンス、動的システム扱い、AI サイバーセキュリティ、サプライヤー資格、医療機器としての AI、監査対応 |

AI ライフサイクル（GAMP AI Guide）〔事実〕：

1. **Concept（構想）**: Intended Use の厳密な定義、静的/動的の決定、予備的リスクアセスメント、build-buy-partner 判断
2. **Project（プロジェクト）**: データガバナンス（データ出所、リネージ、品質、バイアス評価、train/test 分離）、モデル開発（実験追跡）、性能指標定義、IQ/OQ/PQ（モデル特有テスト含む）
3. **Operation（運用）**: 性能・ドリフト・データ品質の継続監視、監査再構成可能なログ、定期レビュー、AI 向け変更管理（再訓練が再適格をトリガする条件）
4. **Retirement（リタイア）**: モデル廃止、訓練データ・モデル成果物の規制保持期間中のアーカイブ、移行経路

出典:
- ISPE GAMP AI Guide: https://ispe.org/publications/guidance-documents/gamp-guide-artificial-intelligence
- Clinstacks GAMP 5 AI Guide 解説: https://clinstacks.com/compliance/gamp-5-ispe-ai-guide
- Intuition Labs GAMP 5 AI: https://intuitionlabs.ai/articles/validating-ai-gxp-gamp5-guide

---

## 2. Critical/Non-critical AI 分類と auto_cell L0–L3 のマッピング

### 2.1 Critical AI の定義（Annex 22 上）

Annex 22 における **Critical AI** は、「患者安全、製品品質、GMP 関連データ完全性に直接影響を与える決定に関与する AI/ML モデル」と定義される〔事実〕。

A 層で Critical AI として扱う可能性があるのは、原則として **L1 決定的ルール**で実装される制御経路に AI/ML を導入する場合に限られる。具体的候補〔推定〕：

- **in-line Raman による代謝物予測 → 灌流率制御**: 閉ループ入力として使う場合、PLS 等の静的決定論的モデルが該当。
- **凝集体画像 DL → 継代/撹拌判断**: 自発分化・品質判定に使う場合、静的画像分類モデルが該当。
- **L2 BO の獲得関数・GP 予測**: run 間探索の判断材料。静的モデルとして扱えるが、出力が setpoint 提案に直結する場合は準クリティカル。

### 2.2 Non-critical AI の定義

**Non-critical AI** は、GMP クリティカルな決定に直接影響しない AI。A 層では以下が該当〔推定〕：

- **L3 LLM オーケストレータ**: 承認要求文書作成、イベント要約、HMI 説明、SOP ドラフト生成、研究者対話。
- **実験レポート・傾向分析の生成 AI 支援**: 非 GMP 判断の文書化。
- **予測保全・アドバイザリ入力**: 製品品質に直接影響しない限定的用途。

### 2.3 L0–L3 と Annex 22 / EU AI Act / GAMP の対応マッピング

| 層 | 構成要素 | Annex 22 分類 | EU AI Act 推定分類 | GAMP カテゴリ案 | 技術的統制 |
|---|---|---|---|---|---|
| **L0** | 局所 PID（温度/pH/DO/撹拌） | AI ではない決定論的制御器。Annex 22 適用外 | 非 AI | Cat.1（インフラ）+ Cat.4（設定済み機器） | ベンダ IQ/OQ、設定点凍結、ALCOA-lite 監査ログ |
| **L1** | レシピ DSL/状態機械/ルールエンジン | **明示的ルールによるクリティカル制御**。Annex 22 の「明示的にプログラムされた」モデルではないが、クリティカル経路 | 非高リスク（R&D 一次） | Cat.4/5（カスタムアプリ） | `validate_tool_call`、CPP 包絡線、監査ログ、EBR-like 記録、静的決定論的証明 |
| **L2** | Ax/BoTorch バッチ BO + GP | **静的モデルとして扱う**（訓練データ固定・シード固定）。run 間最適化でクリティカル経路には触れない | R&D: 非高リスク〔推定〕。GMP 製造: 準クリティカル | Cat.4/5（設定済み/カスタム AI） | データ分離、モデルカード、獲得関数説明、信頼度（GP 事後分散）、ドリフト監視 |
| **L3** | 薄い LLM オーケストレータ | **非クリティカルのみ**。HITL 必須。クリティカル制御には絶対に使わない | 限定リスク/透明性義務（非クリティカル用途）〔推定〕 | Cat.5（カスタム AI）+ 非クリティカル用途限定 | プロンプトバージョニング、入出力ログ、人承認、RAG により承認済み SOP のみ参照 |

**重要**〔設計判断〕: A 層 v1 では、クリティカル制御経路に AI/ML を導入しない。L1 は明示的ルール・状態機械で実装し、Annex 22 の厳格な AI 検証要件は将来の Raman PLS や画像 DL 等に限定される。

### 2.4 静的・決定論的モデルの証明方法

Annex 22 が要求する「static + deterministic」を満たすため、A 層で AI/ML モデルを使う場合は以下を実施する〔推定：業界解釈〕：

| 証明項目 | 技術的アプローチ | 備考 |
|---|---|---|
| 凍結パラメータ | トレーニング後に重み・パラメータを固定し、SHA-256 等でバージョン管理 | 変更時は再検証 |
| 固定乱数シード | Python/NumPy/PyTorch 乱数シード固定 | ニューラルネットの場合必須 |
| 決定論的推論環境 | 同じライブラリバージョン・CUDA バージョン・ハードウェアで実行 | 浮動小数点の非決定性を最小化 |
| 再現性テスト | 同一入力 → 同一出力を CI/テストセットで検証 | plant_model 回帰テストと同じ考え方 |
| モデルカード | 意図用途、訓練データ、前処理、評価指標、制限事項を文書化 | Annex 22 3.1/4.1/5.1 に対応 |

---

## 3. R&D 一次で導入する技術的統制の優先順位

A 層 R&D 一次で導入可能な技術的統制を、コスト・効果・優先度で整理する。

| 統制 | 実装方針 | コスト | 優先度 | 対応 Annex 22 章 |
|---|---|---|---|---|
| **ALCOA-lite 監査ログ** | 全副作用ツール呼び出しを `who/when/what/why` で構造化ログ化。承認状態遷移・イベント・センサ取り込みも含む。失敗/却下/タイムアウトも保存。NTP 同期 UTC、correlation ID で因果追跡。 | 低 | **P0（最高）** | 2.Principles, 10.Operation |
| **Intended Use 文書化** | L2 BO/GP、将来 Raman PLS/画像 DL 用のテンプレート作成。タスク、入力データ特性、限界・バイアス、サブグループ、置き換える工程の性能基準を文書化・承認。 | 低 | **P0** | 3.Intended Use, 4.Acceptance Criteria |
| **データ分離（train/valid/test）** | Git LFS/オブジェクトストレージで技術的分離。リポジトリアクセス制御。同一データを訓練と最終テストに使わない。 | 低 | **P0** | 5.Test Data, 6.Test Data Independency |
| **Human-on-the-loop（HITL）承認ワークフロー** | 包絡線外 setpoint、`trigger_passage`、BO 提案採用、低信頼度 AI 出力は研究者承認。承認履歴を append-only で保存。 | 中 | **P0** | 3.Intended Use, 9.Confidence, 10.Operation |
| **静的決定論的証明** | モデル重みの checksum、固定シード、再現性テスト、モデルカードを CI 化。L1 ルールエンジンも対象。 | 中 | **P1（高）** | 1.Scope, 7.Test Execution, 10.Operation |
| **信頼度スコア層** | L2 BO: GP 事後分散 → 信頼度。将来 Raman PLS: Q 残差/Hotelling T²。画像 DL: ensemble/MC dropout 分散。閾値未満で自動 HITL エスカレーション。 | 中 | **P1** | 9.Confidence |
| **XAI / feature attribution** | L2 BO: 獲得関数・GP 事後分布の可視化。画像 DL: SHAP/Grad-CAM。L1 ルール: ルール ID・適用条件・参照 CPP 値をログ化。 | 中 | **P1** | 8.Explainability |
| **ドリフト監視** | 入力サンプル空間（glucose/lactate 分布、凝集体径分布）の変化を検知し、再校正/再検証トリガ。 | 中 | **P2（中）** | 10.Operation |
| **職員独立性（dual control）** | R&D では「4-eyes / dual control」で緩和。test データ閲覧者は訓練・検証に関与不可。 | 低〜中 | **P1** | 6.Test Data Independency |
| **プロンプトバージョニング** | L3 LLM のシステムプロンプト・few-shot 例を Git 管理。バージョンごとに入出力評価。 | 低 | **P1** | 10.Operation |
| **電子署名（軽量版）** | R&D 一次: PIN/パスフレーズ + 監査ログ。GMP 移行時に Part 11/Annex 11 完全署名へ移行。 | 中 | **P2** | Annex 11, Part 11 |
| **WORM ストレージ** | 生データ・画像・監査ログの不変アーカイブ。R&D ではオブジェクトストレージのバージョニングで代替可。 | 中〜高 | **P3（低/GMP 移行時）** | Annex 11, Part 11 |

### 3.1 R&D 一次フェーズ別導入ロードマップ

| フェーズ | 導入統制 | ゴール |
|---|---|---|
| **v1 / Phase 1（0–12 ヶ月）** | ALCOA-lite 監査ログ、Intended Use テンプレート、データ分離設計、HITL 承認ワークフロー、プロンプトバージョニング | 閉ループを回しつつ、将来の Annex 22 対応骨格を構築 |
| **Phase 2（12–24 ヶ月）** | 静的決定論的証明の CI 化、信頼度スコア、XAI、ドリフト監視、職員独立性ポリシー | Raman PLS 等の静的 AI 導入に備える |
| **Phase 3（24–48 ヶ月）** | 電子署名拡張、WORM、完全職員独立性、IQ/OQ/PQ、性能等価性実証 | GMP 完全準拠へ移行 |

---

## 4. 各 AI/ML コンポーネントの GAMP カテゴリ分類案

### 4.1 GAMP 5 カテゴリの簡易整理

| カテゴリ | 内容 | 例 |
|---|---|---|
| **Cat.1** | インフラストラクチャ・OS・DB・ネットワーク | Linux、PostgreSQL、MQTT broker、NTP |
| **Cat.3** | 標準製品（設定変更不可、又は変更が限定的） | 組み込み OPC-UA スタック、標準ライブラリ |
| **Cat.4** | 設定済み製品（パラメタ・設定で適用） | 設定済み MES/LIMS、BO ライブラリ（Ax/BoTorch） |
| **Cat.5** | カスタムアプリケーション・カスタム AI | 自社開発 L1 ルールエンジン、L2 BO ラッパ、L3 LLM オーケストレータ |

### 4.2 auto_cell A 層の GAMP カテゴリ分類案

| コンポーネント | 推定 GAMP カテゴリ | 理由 | 検証アプローチ |
|---|---|---|---|
| **OS / DB / MQTT broker / NTP** | Cat.1 | インフラ基盤 | IQ（インストール確認）、構成管理 |
| **OPC-UA / LADS / SiLA2 SDK** | Cat.3/4 | 標準/設定済みミドルウェア | ベンダ文書確認、設定検証 |
| **physical-ai-core（MQTT 層）** | Cat.4/5 | 設定・拡張が必要なフレームワーク | IQ/OQ、拡張部分のテスト |
| **L1 決定的レシピ/ルールエンジン** | **Cat.5** | カスタム開発のクリティカル制御ロジック | ユニットテスト、イベント網羅テスト、plant_model 回帰テスト、コードレビュー |
| **L2 BO/GP ラッパ** | **Cat.4/5** | 設定済みライブラリ（Ax/BoTorch）＋カスタム目的関数/制約 | OQ/PQ、再現性テスト、モデルカード、データ分離確認 |
| **L3 LLM オーケストレータ** | **Cat.5** | カスタム AI、非クリティカル用途限定 | プロンプトバージョニング、入出力評価、HITL ログ、RAG 制限 |
| **Raman PLS（将来）** | Cat.4/5 | chemometric ソフト＋カスタムモデル | 校正・検証、Q 残差監視、再現性テスト |
| **画像 DL 品質代理指標（将来）** | Cat.5 | カスタム ML モデル | 性能指標、SHAP/Grad-CAM、OOD 検出 |
| **監査ログ / event_store** | Cat.4/5 | カスタムデータ層 | ALCOA-lite 検証、リストアテスト |

---

## 5. データ分離・職員独立性の軽量実装案

### 5.1 データ分離の実装案

Annex 22 6.Test Data Independency を R&D 段階から設計に組み込む。

| 項目 | R&D 一次実装案 | GMP 移行時拡張 |
|---|---|---|
| **リポジトリ分離** | `data/train/`、`data/valid/`、`data/test/` を Git LFS 又はオブジェクトストレージで分離。アクセス制御はロールベース。 | 物理的分離、異なる環境、WORM アーカイブ |
| **train/valid/test 分離** | 実験設計時に split 比率を文書化。random seed 固定。 | 層別化（細胞株、スケール、季節）を厳密化 |
| **test データ保護** | test データへのアクセスを audit trail で記録。開発者は原則読み取り不可。 | 完全なアクセス制御、独立した QA チスト管理 |
| **物理試料の再利用禁止** | 同一バッチの画像・スペクトルを訓練と最終テストに使わない運用ルール。 | SOP 化、システム的ブロック |
| **リネージ追跡** | DVC 又は MLflow でデータ・モデル・実験のリネージを追跡。 | 完全なデータリネージシステム |

### 5.2 職員独立性の軽量実装案

小規模 R&D 組織では完全な職務分離は困難。Annex 22 6.5 の「4-eyes / dual control」緩和を活用する。

| 原則 | R&D 一次実装案 |
|---|---|
| **test データ閲覧者の訓練・検証からの分離** | test データにアクセスしたメンバーは、同じモデルの訓練・検証をペア（4-eyes）で行う場合のみ参加可。 |
| **dual control** | 重要なモデル承認・テスト結果レビューは 2 名の署名。 |
| **ロール分離** | 研究者（モデル訓練）/ オペレータ（運用）/ システム（インフラ）の簡易ロールを分離。 |
| **アクセスログ** | 誰がいつどのデータセットにアクセスしたかを append-only で記録。 |

### 5.3 データ分離・職員独立性チェックリスト（R&D 軽量版）

```markdown
- [ ] train/valid/test の split 比率と stratification 方針を文書化済
- [ ] test データセットが訓練・検証コードから分離されている（パス分離）
- [ ] test データへのアクセスに audit trail あり
- [ ] test データを閲覧した者が同モデルの訓練・検証を単独で行わない（dual control）
- [ ] 同一物理試料（バッチ、画像、スペクトル）が訓練と最終テストに重複していない
- [ ] データ前処理パイプラインがバージョン管理され、再現可能
- [ ] データセットの checksum（SHA-256）を記録
- [ ] データリネージツール（DVC/MLflow）で run ごとに追跡
```

---

## 6. 静的決定論的証明のチェックリスト

A 層で AI/ML モデルを運用する際の「static + deterministic」証明手順。

### 6.1 モデル凍結・バージョン管理

```markdown
- [ ] トレーニング後、モデル重み・パラメータを凍結
- [ ] モデル成果物（weights, config, scaler, vocabulary）に SHA-256 checksum を付与
- [ ] Git tag でモデルバージョンを管理（例: `model/v1.2.3-raman-pls`）
- [ ] 訓練に使用したデータセットのバージョンも同時に記録
- [ ] モデルカードを作成し、Intended Use・性能・制限を文書化
- [ ] 変更時は影響評価と再検証を実施
```

### 6.2 乱数シード・再現性

```markdown
- [ ] Python random seed 固定
- [ ] NumPy random seed 固定
- [ ] PyTorch/TensorFlow seed 固定（該当する場合）
- [ ] CUDA deterministic モード有効化（該当する場合）
- [ ] 同一ハードウェア・ライブラリバージョンで再現性テストを実施
- [ ] CI で同一入力 → 同一出力のテストを自動化
```

### 6.3 L1 決定的ルールエンジン向け証明

```markdown
- [ ] レシピ DSL/状態機械の文法を正式に定義
- [ ] 全状態遷移とアクションを列挙
- [ ] 到達不能状態・デッドロックがないことを検証
- [ ] 同一初期条件・同一入力系列で同一出力系列を返すことを CI で検証
- [ ] `validate_tool_call` の包絡線・ramp 制限がすべての経路で発動することをテスト
- [ ] ルール変更時は golden test の更新とレビューを義務付ける
```

### 6.4 モデルカードテンプレート（R&D 軽量版）

```markdown
# Model Card: <モデル名>

## 1. Intended Use
- 自動化/支援するタスク:
- 対象プロセス:
- 対象細胞株/培地/スケール:
- 置き換える工程/手動プロセス:

## 2. Input Data
- 入力変数と範囲:
- サンプリング頻度:
- 前処理:
- 既知のバイアスと限界:

## 3. Training Data
- データソース:
- バッチ数/サンプル数:
- 時間範囲:
- 正解ラベルの取得方法:
- train/valid/test split:

## 4. Model
- アルゴリズム:
- ハイパーパラメータ:
- 乱数シード:
- 凍結日:

## 5. Performance
- 評価指標:
- 全データでの性能:
- サブグループ別性能:
- 置き換える工程の性能との比較:

## 6. Limitations
- 対象外の入力空間:
- 既知の失敗モード:
- 再校正トリガ:

## 7. Approval
- 作成者:
- レビュアー（SME）:
- QA:
- 承認日:
```

---

## 7. プロンプトバージョニング・入出力ログの要件

### 7.1 L3 LLM オーケストレータの位置づけ

L3 LLM は **非クリティカル用途のみ** とし、以下に限定する〔設計判断〕：

- 承認要求文書のドラフト作成
- イベント・異常の要約と HMI 説明
- SOP ・レポートドラフト生成
- 研究者対話・問い合わせ対応
- 新規例外の初期分類（最終判断は人）

**絶対に許可しない用途**：setpoint 最終決定、安全インターロック上書き、無菌バリア無効化、クリティカルな工程判断。

### 7.2 プロンプトバージョニング要件

```markdown
- [ ] システムプロンプトは Git 管理（`prompts/system/v{major}.{minor}.md`）
- [ ] few-shot 例も Git 管理
- [ ] プロンプト変更時はバージョンタグ付与
- [ ] 各プロンプトバージョンごとに入出力評価テストを実施
- [ ] 本番推論時は使用プロンプトのバージョンをログに記録
- [ ] RAG により、参照可能な文書は承認済み SOP/レポートのみに限定
```

### 7.3 入出力ログ要件

```markdown
- [ ] 入力: ユーザー問い合わせ、現在の CPP 要約、使用したツールスキーマ、プロンプトバージョン
- [ ] 出力: LLM の生応答、生成したツール呼び出し、根拠となった情報源
- [ ] 思考過程（chain-of-thought）があれば記録
- [ ] 承認/却下/修正の履歴を同一 correlation_id で紐付け
- [ ] ログは append-only、タイムスタンプ付き、NTP 同期
- [ ] 個人情報・機密情報のマスキング
- [ ] 保持期間を定義（R&D: プロジェクト期間＋α、GMP: 規制要求期間）
```

### 7.4 LLM 入出力ログスキーマ例

```json
{
  "log_id": "llm-uuid",
  "correlation_id": "cmd-uuid",
  "timestamp_utc": "2026-06-30T06:54:11Z",
  "prompt_version": "system/v1.2.3",
  "model_name": "gpt-4o",
  "model_version": "2026-05-01",
  "input_summary": {
    "user_request": "trigger_passage の承認依頼を作成",
    "culture_unit_id": "cu-001",
    "current_phase": "perfusion_ramp",
    "relevant_events": ["vcd_target_reached"]
  },
  "output": {
    "generated_text": "...",
    "tool_calls": [],
    "citations": ["SOP-CELL-001"]
  },
  "approval": {
    "status": "pending",
    "requested_by": "system",
    "approved_by": null
  },
  "retention_until": "2031-06-30"
}
```

---

## 8. GMP 移行時のギャップ分析

R&D 一次の軽量実装から GMP 完全準拠への移行ギャップ。

| 領域 | R&D 一次（v1） | GMP 移行時 | ギャップ |
|---|---|---|---|
| **電子署名** | PIN/パスフレーズ + 監査ログ（ALCOA-lite） | 21 CFR Part 11 / Annex 11 完全署名（ID・パスワードの一意リンク、再署名、署名意味付け） | 大：IdP 導入、署名ワークフロー、再署名ポリシー |
| **職員独立性** | 研究者/オペレータ/システムの簡易ロール分離、4-eyes 緩和 | QA/製造/QC/IT/データサイエンスの明確な役割分離、SOP 化 | 大：組織・SOP の整備 |
| **データ分離** | train/test リポジトリ分離、dual control | 物理的分離、WORM、定期レビュー SOP | 中：インフラ・運用コスト |
| **監査証跡** | 構造化ログ + 簡易ハッシュチェーン | WORM ストレージ + 定期レビュー + 完全トレーサビリティ | 中：ストレージ・レビュー体制 |
| **変更管理** | Git バージョン管理 + 承認ワークフロー | GAMP IQ/OQ/PQ、影響評価、再検証 SOP | 大：文書化・承認階層 |
| **性能等価性** | 研究者合意ベース | AI/ML モデルが置き換える手動工程の性能以上であることを文書化 | 大：ベースライン性能データ取得 |
| **ベンダー資格** | 主観的選定 | OPC-UA/LADS デバイス、Raman、画像分析器等の AI 関連部分のサプライヤー監査 | 中〜大：監査・文書化 |
| **ドリフト監視** | 入力分布変化の簡易監視 | 性能・ドリフト・入力空間の定期レビュー、再検証サイクル | 中：SOP 化・レビュー体制 |
| **リタイアメント** | プロジェクト終了時の削除 | 訓練データ・モデル成果物の規制保持期間中のアーカイブ | 中：アーカイブ戦略 |

### 8.1 GMP 移行準備度チェックリスト

```markdown
- [ ] すべての AI/ML ユースケースをインベントリ化し、critical/non-critical に分類済
- [ ] 各モデルの Intended Use 文書が承認済
- [ ] 各モデルの性能等価性（置き換える工程との比較）が文書化済
- [ ] train/valid/test データの完全な分離とリネージ追跡が実装済
- [ ] 職員独立性ポリシーが SOP 化され、組織ロールが定義済
- [ ] 電子署名システムが Part 11/Annex 11 要件を満たす設計
- [ ] WORM アーカイブ戦略が定義済
- [ ] ドリフト監視と再検証トリガが SOP 化済
- [ ] ベンダー監査計画が作成済
- [ ] 変更管理・CAPA プロセスが AI 向けに拡張済
```

---

## 9. 業界事例・ベストプラクティス

### 9.1 製薬 R&D/製造での Annex 22-ready システム事例

| 事例 | 用途 | AI 技術 | 統制 | 出典 |
|---|---|---|---|---|
| **製粒プロセスのリアルタイムモニタリング** | 連続製粒ラインの粒子径分布監視 | 画像分析＋回帰 | SHAP 説明、信頼度スコア、HITL レビュー、QA 日次レビュー | MDPI Information 2025, 16, 1082 |
| **無菌充填の予測保全** | 充填ラインの設備故障予測 | 時系列分析・異常検知 | 保守担当者が予測を承認/却下、製品品質に直接影響しない非クリティカル用途 | 同上 |
| **逸脱の根本原因分析支援** | 過去逸脱データのクラスタリングと原因提案 | LLM/クラスタリング | 調査者が提案をレビュー、人間判断が一次、AI は助言的 | 同上 |
| **品質影響リコールエージェント** | リコール時の影響批次・顧客特定（決定的）と通知文ドラフト（LLM） | 決定論的トレーサビリティ + LLM | トレーサビリティは決定論的。通知文は人間レビュー後送信。 | Cegeka blog 2026 |

### 9.2 Annex 22-ready 実装の共通パターン

1. **クリティカル経路は決定論的に**：重要な分類・制御判断は、可能な限り明示的ルール・決定論的モデルで実装する。
2. **AI はアドバイザリ/承認仲介に限定**：動的・確率的・生成 AI は非クリティカル用途に限定し、HITL を必須とする。
3. **信頼度スコアと説明性を付与**：すべての AI 出力に信頼度と根拠を付与し、低信頼度は自動エスカレーション。
4. **データ分離と職員独立性を早期から設計**：小規模 R&D でも dual control で緩和しつつ、GMP 移行を見据えた分離を維持。
5. **監査証跡を全面化**：AI の入出力、承認、変更、ドリフトをすべてログ化。
6. **段階的拡張**：R&D 一次で ALCOA-lite・HITL・データ分離を導入し、GMP 移行時に電子署名・WORM・IQ/OQ/PQ を追加。

---

## 10. 結論・設計への反映

1. **ADR-0001 の L0–L3 分離は Annex 22 と本質的に整合**〔推定〕。L0/L1 は決定的、L2 BO/GP は静的モデルとして扱える、L3 LLM は非クリティカル用途に限定する設計を維持する。
2. **R&D 一次では 9 本柱の技術的統制を Phase 1 で導入**〔設計判断〕：ALCOA-lite 監査ログ、Intended Use、データ分離、職員独立性、静的決定論的証明、XAI、信頼度スコア、ドリフト監視、HITL。
3. **電子署名・WORM・完全職員独立性は GMP 移行時に段階的拡張**〔推定〕。R&D 一次で過剰な規制コストをかける必要はない。
4. **L3 LLM は R&D 時点から非クリティカル用途に限定**〔設計判断〕。per-cycle 制御やクリティカル判断に絶対に使わない。
5. **EU AI Act は A 層 R&D 一次では高リスク該当しにくい**〔推定〕が、将来製品化・医療機器化の可能性がある場合は並行して検討が必要。
6. **GAMP5 AI Guide は Annex 22 の実装方法論**として活用でき、L2 BO/GP を Cat.4/5、L3 LLM を Cat.5（非クリティカル）として扱うのが現実的。

---

## 11. 出典リスト

| ID | タイトル | URL/DOI/ガイダンス名 | 確度 |
|---|---|---|---|
| src_pics_annex22_draft | EudraLex Volume 4 — Draft Annex 22: Artificial Intelligence (July 2025) | https://health.ec.europa.eu/document/download/5f38a92d-bb8e-4264-8898-ea076e926db6_en?filename=mp_vol4_chap4_annex22_consultation_guideline_en.pdf | 事実 |
| src_pics_news | PIC/S news — Joint stakeholders consultation on Chapter 4 / Annex 11 / Annex 22 | https://picscheme.org/en/news/joint-stakeholders-consultation-on-the-revision-of-chapter-4 | 事実 |
| src_ec_consult | EC — Stakeholders' Consultation on EudraLex Volume 4 Chapter 4, Annex 11 and new Annex 22 | https://health.ec.europa.eu/consultations/stakeholders-consultation-eudralex-volume-4-good-manufacturing-practice-guidelines-chapter-4-annex_en | 事実 |
| src_eu_ai_act | Regulation (EU) 2024/1689 — Artificial Intelligence Act | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689 | 事実 |
| src_nature_ai_act_meddevice | Navigating the EU AI Act: implications for regulated digital medical products | https://www.nature.com/articles/s41746-024-01232-3 | 事実 |
| src_raps_ai_act_class | EU Commission drafts guidelines on classifying high-risk systems under the AI Act | https://www.raps.org/resource/eu-commission-drafts-guidelines-on-classifying-high-risk-systems-under-the-ai-act.html | 事実 |
| src_gamp5_ai | ISPE GAMP Guide: Artificial Intelligence (2025) | https://ispe.org/publications/guidance-documents/gamp-guide-artificial-intelligence | 事実 |
| src_gamp5_2nd | ISPE GAMP 5 Guide: A Risk-Based Approach to Compliant GxP Computerized Systems, 2nd Edition (2022) | https://ispe.org/publications/guidance-documents/gamp-5-guide-2nd-edition | 事実 |
| src_clinstacks_gamp_ai | GAMP 5 & the ISPE AI Guide: Translating the 290-Page Framework into Actionable Validation | https://clinstacks.com/compliance/gamp-5-ispe-ai-guide | 推定 |
| src_intuition_gamp_ai | Validating AI in GxP: GAMP 5 & Risk-Based Guide | https://intuitionlabs.ai/articles/validating-ai-gxp-gamp5-guide | 推定 |
| src_intuition_annex22 | EU GMP Annex 22: AI Compliance in Pharma Manufacturing | https://intuitionlabs.ai/articles/eu-gmp-annex-22-ai-compliance-pharma | 推定 |
| src_merit_annex22 | EU GMP Annex 22: The New AI Regulatory Standard for Biopharma & Medical Device Manufacturing | https://meritsolutions.com/blog-annex-22-ai-pharma-regulation/ | 推定 |
| src_pharmout_annex22 | Draft Publication of EU and PIC/S GMP Annex 22 Artificial Intelligence | https://www.pharmout.net/annex-22-artificial-intelligence/ | 推定 |
| src_regask_annex22 | Decoding the New PIC/S Annex 22 for Regulatory Teams | https://regask.com/ai-gmp-decoding-new-pics-annex-22-regulatory-teams/ | 推定 |
| src_pwc_annex22 | Annex 22: Making AI work in a Good Practice (GxP) environment | https://www.pwc.be/en/news-publications/2026/annex-22-making-ai-work-in-a-good-practice-gxp-environment.html | 推定 |
| src_mdpi_hitl_opv | Human-in-the-Loop AI Use in Ongoing Process Verification in the Pharmaceutical Industry | https://www.mdpi.com/2078-2489/16/12/1082 | 事実/推定 |
| src_cegeka_recall | What Pharma Can (and Cannot) Do with AI Under Annex 22 | https://www.cegeka.com/en/blogs/what-pharma-can-and-cannot-do-with-ai-under-annex-22 | 推定 |
| src_fda_csa | FDA — Computer Software Assurance for Production and Quality System Software | https://www.fda.gov/regulatory-information/search-fda-guidance-documents/computer-software-assurance-production-and-quality-system-software | 事実 |
| src_part11 | 21 CFR Part 11 — Electronic Records; Electronic Signatures | https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11 | 事実 |
| src_alcoa_sware | ALCOA Principles in Pharma: Your Complete Guide to Data Integrity Compliance | https://www.sware.com/blog/alcoa-principles-in-pharma | 推定 |
| src_worm_biotech | The Role of WORM Compliance in Biotech Data Integrity | https://intuitionlabs.ai/pdfs/the-role-of-worm-compliance-in-biotech-data-integrity.pdf | 推定 |
| adr0001 | ADR-0001: Control architecture | docs/design/adr/0001-control-architecture.md | 事実 |
| kg_bridge | KG → auto_cell 設計ブリッジ | docs/design/kg_to_auto_cell.md | 事実 |
| annex22_roadmap | PIC/S GMP Annex 22 対応ロードマップ | docs/design/ground_knowledge/additional_annex22_roadmap.md | 事実 |
| integrated_report | 追加調査統合レポート | docs/design/ground_knowledge/additional_investigation_integrated.md | 事実 |
| missing_assets | 閉ループ実現に必要な不足アセット | docs/design/closed_loop_planning/02_missing_assets_for_closed_loop.md | 事実 |

---

*本レポートは A 層（iPSC 浮遊/凝集体バイオリアクター制御）の R&D 一次/Annex 22-ready 設計に限定。full GMP 移行時にはプログラム全体の QMS/CSV/規制チームによる詳細評価が必要。*
