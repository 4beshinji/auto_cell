# 品質読み出し → BO 目的関数（#11/#12）調査レポート

- 日付: 2026-06-15 ／ 手法: deep-research（5角度・24ソース・115主張→上位25を3票検証→23確定/2否決）＋ 私による一次検証（Kanda eLife 2022）
- 対象: iPSC 浮遊拡大の品質/同一性/多能性読み出しを「run 毎に測れる（BO 目的関数）」か「offline/run単位（合格ゲート）」かに分類し、R&D 用 BO 目的関数の現実的構成を出す。
- 反映先: `../../design/kg_to_auto_cell.md` §4.3、ADR-0001 follow-up（目的関数定義）、KG `qccrit`/`bbo`。

## 結論サマリ

正準な分子的品質 assay は**どれも厳密な at-line ではない**（破壊サンプリング・分〜日）。BO 目的関数に現実的なのは
**per-run の連続スカラ化できる run 単位指標**。同一性・ゲノム安定性は一様に offline・多日・pass/fail ＝ **BO 制約/
バンキング cadence ゲート**であって目的関数項ではない。

## BO 適性マップ

### A. per-run 目的関数項（連続・スカラ化可・run 毎に測れる）

| 読み出し | assay | turnaround | 破壊性 | スカラ化 | BO 適性 |
|---|---|---|---|---|---|
| 収量（VCD/fold） | capacitance / 計数（P5） | 連続/run | 非破壊(capacitance) | 連続値 | ✅目的項 |
| 生存率 | Nova FLEX2 / 画像 | ~分 | 破壊(サンプル) | 連続% | ✅目的項 |
| **多能性 %陽性** | フローサイト（OCT3/4, TRA-1-60, **SSEA5** が cross-lab 最ロバスト; SSEA4 は残存検出向き） | 分〜時間 | **破壊サンプリング**（at-line でない） | 連続%（実務は多マーカー pass/fail ゲート化: 例 ≥3マーカー各≥75% or >70%） | ✅目的項（per-run サンプル） |
| （条件付き）ラベルフリー画像代理 | 明視野/位相差/DHM＋DL | 連続 | 非破壊 | 連続 | ⚠️**未確立**（DR で確証claimゼロ＝最大ギャップ） |

### B. offline/periodic 制約・ゲート（目的関数項にしない）

| 読み出し | assay | turnaround | BO での扱い |
|---|---|---|---|
| 同一性 | STR profiling（ANSI/ATCC ASN-0002, ≥13 loci, %一致スカラ化可） | 多日・periodic | pass/fail 制約（donor baseline 照合） |
| 核型/ゲノム安定性 | G-band（7-10日, ~5-10Mb 分解能）/ KaryoStat(3-4日) / SNP-aCGH（モザイクは≥20%のみ確実） | 多日 | 制約。**~70%の株が CNV 保有→periodic 監視必須**（初期＋~10継代毎） |
| 残存未分化（安全） | 上清 **miR-302b（0.001%, LIN28 の10倍感度・非破壊）** / 細胞内 LIN28 | 時間 | 最小化制約。miR-302b は非破壊 run 候補だが**単一 RPE 研究**で要検証 |
| 三胚葉分化能 | ScoreCard qPCR（per-胚葉 Z-score 連続値, teratoma の5-10倍速だが EB依存・多日） / STEMdiff trilineage（~1週） | 多日 | offline 事後/cadence 目的 or 制約 |

## 推奨 BO 目的関数（R&D, 測定可能性ベース）

- **per-run 連続目的**: `J = 収量(VCD/fold) × 生存率 × 多能性%陽性`（＋検証できれば label-free 非破壊代理）。単一加重スカラで開始。
- **offline/periodic 制約（safe/constrained BO）**: 同一性(STR)・核型/CNV・残存未分化 を end-of-run/バンキング cadence の pass/fail ゲートに。→ ADR-0001 の constrained/safe BO と整合。
- ゲノム安定性は per-run でなく **periodic（初期＋~10継代毎）** の制約として課す。

## 先例（一次検証済）: Kanda et al. 2022 eLife（iPSC BO の正準例）

- 目的: **単一目的＝画像由来の色素化スコア**（day34 の色素 RPE 細胞の面積比＝分化誘導効率）。自動画像解析（Gaussianブラー→背景減算→閾値二値化）で測定＝**非破壊・自動**。
- 手法: **batch BO**（GP回帰＋Expected Improvement＋Batch Contextual Local Penalization, **GPyOpt** ベース）。7パラメタ・~2億通り。
- 規模/成果: 143 条件 / 111 日 / 3 ラウンド → 事前最適化比 **88%改善**（スコア 0.91 vs 0.43）。
- 含意: ①**単一目的 batch BO が iPSC で実証済**（auto_cell の Ax/BoTorch は現代等価）。②**画像由来スカラを目的にできる**（Kanda は分化の色素面積）。ただし**分化ドメイン**で、拡大(expansion)の品質代理画像は未確立（→ 拡大では測定 pluripotency%＋yield＋viability を使う）。

## Caveats

- **label-free 画像代理（調査4）は確証claimゼロ＝最大ギャップ**: CellXpress.ai/Ovizio/DL の per-run 多能性予測精度・検証状況を一次で主張できない。目的関数では「検証できれば」の条件付き項に留める。
- **拡大 BO の公開目的関数は未特定**: Kanda は分化(RPE)。拡大の published scalarization は未確認 → 上記推奨は測定可能性からの合成推論。
- miR-302b は単一 RPE 研究、浮遊拡大への一般化は未検証。GMP 閾値（≥3マーカー≥75% 等）は lab 固有でゲート構造のみ流用。
- 否決2件: フロー%再現性は標準化前提のみ(1-2)、上清 ddPCR 非侵襲 CNV(1-2)→**非侵襲ゲノム screening は不支持＝ゲノム安定性は offline ゲートのまま**。

## Open（次調査候補）

- label-free/DL 画像代理の査読済 per-run 多能性予測精度（#検証が取れれば目的関数の非破壊項に昇格）。
- iPSC **拡大** BO の公開目的構成（単一加重 vs Pareto 多目的、weight）。
- 浮遊拡大での非破壊 run 品質サロゲート（上清 miRNA、代謝キネティクス、OUR 等）。
