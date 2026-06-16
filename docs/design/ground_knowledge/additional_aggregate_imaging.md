# 追加調査：浮遊凝集体画像解析（Aggregate imaging for iPSC suspension）

> **担当**: Aggregate imaging for iPSC suspension 調査 Agent  
> **Mode**: A 層制御システム追加調査  
> **Date**: 2026-06-16  
> **Scope**: iPSC 浮遊/凝集体バイオリアクター制御における凝集体径・形態の at-line/in-line 計測と、label-free DL による品質代理指標

## 1. Executive Summary

`docs/design/alignment_with_downloaded_report.md` は、ダウンロードレポートが「2D confluency/位相差画像中心」であるのに対し、auto_cell A 層が「浮遊凝集体」対象であることを**相違点**として挙げている。本調査はそのギャップを補完する。

**結論**:

1. **凝集体径は v1 で at-line 画像が現実的**: in-line DHM/FBRM は技術的に存在するが、iPSC 凝集体の turn-key 実証・校正は限定的。v1 では at-line 明視野/位相差画像（FlowCam/Kropp 型バイパス顕微鏡または手動サンプリング＋顕微鏡）を主軸とする。〔事実：Borys 2021; Eppendorf App Note 485; StemCell mTeSR 3D マニュアル〕
2. **凝集体径と品質は相関するが単純なしきい値ではない**: 径 150–350 µm（Manstein/Borys 設計値）を超えると拡散制限による未分化性低下・壊死リスクが増大するが、細胞株・培地・撹拌による相互作用が大きい。〔事実/推定：Borys 2021; StemCell マニュアル〕
3. **label-free DL による品質代理指標は有望だが未確定**: 2D コロニー・organoid の明視野/位相差から分化状態を予測する研究は多数あるが、**iPSC 浮遊凝集体**に特化した実証は乏しく、OCT4/SOX2/NANOG 等との定量的対応は未確定。〔推定：Chu 2023; Park 2022; Piotrowski 2021〕
4. **2D 画像解析技術は転移可能だが対象が異なる**: セグメンテーション CNN（U-Net 系）、分類 CNN（ResNet/DenseNet）、時系列 RNN の技術スタックは共通。しかし 2D confluency をそのまま使えず、凝集体の「径・面積・円形度・質感・内部構造」に読み替える必要がある。〔推定〕
5. **Human-on-the-loop は必須**: DL 品質代理指標を BO 目的関数や passage トリガに組み込む場合、低信頼度・外挿域では研究者承認を挟む。〔設計選択：ADR-0001; requirements.md FR-4〕

---

## 2. 調査観点と補完すべき相違点

`additional_tasks_memo.md` §6 および `alignment_with_downloaded_report.md` §4.9 に基づく。

| 観点 | 補完内容 | 重要度 |
|---|---|---|
| at-line/in-line 画像技術 | DHM (Ovizio)、FBRM (CLD)、FlowCam、明視野/位相差の特性・実用性を整理 | 高 |
| 凝集体径・形態と品質 | 径 150–350 µm、>400 µm 壊死リスク、OCT4 発現との関係 | 高 |
| label-free DL 品質推定 | 2D/organoid からの転移可能性、iPSC 凝集体固有の課題 | 中 |
| 2D→凝集体転移 | confluency の非適用、凝集体メトリクスへの置き換え | 高 |
| Human-on-the-loop | DL 代理指標の信頼度に基づく承認フロー | 中 |

---

## 3. 浮遊凝集体計測技術比較

### 3.1 技術マトリクス

| 技術 | 計測原理 | 配置 | iPSC 実証 | 主な出力 | 制約/留保 |
|---|---|---|---|---|---|
| **DHM / Ovizio iLINE-F PRO** | 差分デジタルホログラフィー（D3HM）、位相画像 | in-line（バイオリアクタ接続） | 懸浮細胞・MSC・CAR-T 等で VCD/viability/形態の実証。iPSC 凝集体の turn-key 実証は限定的〔推定〕 | VCD、viability、細胞径、凝集体クラスタ数、形態パラメータ | 光学分解能 1.5 µm、個別凝集体径の絶対精度には校正が必要。OPC UA 対応で LADS 統合しやすい〔事実〕 |
| **FBRM / ParticleTrack** | 回転レーザーの後方散乱から chord length distribution (CLD) | in-line（プローブ） | 結晶化・凝集プロセスで広く使用。iPSC 凝集体への直接適用例は少ない〔推定〕 | CLD（0.5–1000 µm）、カウント/sec | CLD は真の粒径分布ではない。凝集体の非球形・透光性により絶対径変換に誤差。粒子濃度・屈折率に依存〔事実〕 |
| **FlowCam** | フローイメージング顕微鏡（明視野＋ optionally 蛍光） | at-line / offline | 海洋微生物・粒子解析で実績。iPSC 凝集体の報告はあるが少ない〔推定〕 | 2 µm–1 mm の粒子画像、径・面積・円形度・アスペクト比 | サンプリング必要。高濃度・重なり凝集体では計数漏れ。日次運用が現実的〔事実〕 |
| **明視野/位相差顕微鏡（at-line）** | 光学顕微鏡＋画像解析 | at-line（サンプリング） | **iPSC 浮遊凝集体で最も一般的**〔事実〕 | 凝集体径、面積、円形度、分布 | 人の主観・サンプリングバイアス。自動化には Kropp 型バイパス顕微鏡または自動サンプリング＋顕微鏡が必要 |

### 3.2 各技術の詳細

#### DHM / Ovizio iLINE-F PRO

- **原理**: 数字ホログラフィーにより、生細胞の位相画像をラベルフリーで取得。細胞径 2–100 µm、細胞密度 1×10⁵–2×10⁷ cells/mL を計測可能〔事実：Semantics Scholar PDF 引用 Ovizio iLine F; Ovizio datasheet〕。
- **iPSC 凝集体への適用**: 個別細胞・小クランプの計測には強いが、直径 150–350 µm の凝集体内部までの位相解析は、光の散乱・多重散乱により難しく、**表面形態とサイズ分布**が主な出力となる〔推定〕。
- **利点**: 非侵襲、in-line、連続計測、cGMP 対応、OPC UA 対応〔事実：BioProcess Online; ChemoMetec〕。
- **設計位置づけ**: v1 ではオプション。凝集体径の「analog channel」としては、at-line 画像または FBRM プロキシが現実的（`kg_to_auto_cell.md` §4.2 と整合）。

#### FBRM

- **原理**: サファイア窓先端で焦点を合わせたレーザーが高速回転（2 m/s 程度）。粒子が通過すると後方散乱光パルスが発生し、その持続時間×走査速度で chord length を算出。1–1000 µm の CLD を秒間数千回計測〔事実：Mettler Toledo; 各種 FBRM 論文〕。
- **iPSC 凝集体への注意**: 凝集体は球形ではなく透光性が高いため、CLD からの径換算は非自明。Square-weighted CLD で大粒子感度を上げる方法が一般的だが、絶対径は画像法で補正する必要がある〔事実：Chow et al. 2008; 各種 FBRM 論文〕。
- **設計位置づけ**: CLD トレンド監視は有用だが、v1 の passage トリガには**画像法で校正済みの径**を用いる。

#### FlowCam

- **原理**: サンプルを流路で撮影し、個別粒子の画像からサイズ・形態を解析。2 µm–1 mm の範囲〔事実：FlowCam 資料〕。
- **iPSC 凝集体**: 高濃度培養液では凝集体同士の重なり・破砕が生じやすく、自動計数の信頼性は濃度依存。日次 at-line 運用を想定。

#### 明視野/位相差 at-line（現行最も普及）

- **実例**: Eppendorf App Note 485 では、1 L DASGIP Spinner Vessel で hiPSC を 5 日間培養し、毎日 20 mL サンプルを採取、ImageJ で 20 個の凝集体径を手動測定〔事実：Eppendorf App Note 485〕。
- **自動化の可能性**: Kropp et al. 2019（Sci Rep）のバイパス顕微鏡方式、または StemCellFactory の自動撮影＋DL セグメンテーション（Piotrowski 2021）に倣う。

---

## 4. 凝集体径・形態と品質の関係

### 4.1 径と未分化性/壊死

| 主張 | 根拠 | 確度 |
|---|---|---|
| 凝集体径 150–350 µm が A 層の目標範囲 | `kg_to_auto_cell.md` §4; Borys 2021（Vertical-Wheel で day 5 径 169–275 µm） | 事実/設計選択 |
| >400 µm で壊死/未分化性低下のリスク | Borys 2021; StemCell mTeSR 3D マニュアル（>400 µm で core が栄養欠乏・分化/細胞死） | 事実 |
| >300 µm で OCT4 発現が低下する傾向 | escholarship 学位論文（Fig 4.5） | 事実（hPSC） |
| 細胞株・培地・撹拌によって最適径は変動 | Eppendorf App Note 485; Borys 2021 | 事実 |

> ⚠️ 数値は iPSC 株・培地に依存するため、**auto_cell の設計値 150–350 µm は初期仮説であり、実データで再校正が必要**。〔未確定→推定〕

### 4.2 形態パラメータの候補

iPSC 浮遊凝集体の品質代理指標として考えられる画像特徴量：

- **サイズ**: 面積、等価直径、最大/最小径
- **形状**: 円形度（circularity）、アスペクト比、輪郭の粗さ
- **内部構造**: 位相差画像での内部輝度勾配（壊死コアのシグナル低下）
- **分布**: サイズ分布のピーク数（一峰性＝均一、二峰性＝凝集過多/撹拌不良）
- **質感**: 細胞密度・パッキングの均一性

これらを **BO 目的関数の品質項（qccrit 代理）** として使う場合、まず OCT4/SOX2/NANOG/SSEA4/TRA-1-60 等の offline 正解ラベルと回帰/分類モデルを構築する必要がある。〔推定〕

---

## 5. Label-free DL による品質代理指標

### 5.1 先行研究（2D/Organoid）

| 研究 | 対象 | 手法 | 性能 | 出典 |
|---|---|---|---|---|
| Chu et al. 2023 | hiPSC 樹立（リプログラミング） | CNN + DenseNet + U-Net + RNN | 7 日前の iPSC 形成予測 accuracy 0.8 | DOI 10.1016/j.cmpb.2022.107264 |
| Park et al. 2022 | kidney organoid 分化 | DenseNet121（転移学習） | qPCR 発現予測 PCC 0.783 | 10.23876/j.krcp.22.017 |
| Piotrowski et al. 2021 | hPSC 培養ステータス（2D） | マルチクラス DL セグメンテーション | 自動化された培養状態評価 | DOI 10.1016/j.compbiomed.2020.104172 |
| Waisman et al. 2019 | mESC 分化開始早期 | DL | 非常早期の分化を高精度に予測 | Stem Cell Rep 12:845–859 |
| Maddah et al. 2014 | iPSC コロニー品質 | time-lapse + 形態特徴量 | 6 特徴量で good/fair/poor 分類 accuracy 0.80–0.89 | J Lab Autom 19:454–460 |
| Kato et al. 2016 | hPSC コロニー形態 | パラメトリック解析 | 形態カテゴリと遺伝子発現プロファイルが対応 | Sci Rep 6:34009 |

### 5.2 iPSC 浮遊凝集体への転移可能性

**転移可能な技術要素**:

- セグメンテーション: U-Net / DeepLab / Mask R-CNN 系は 2D/3D 球形対象に広く応用可能。
- 分類: ResNet50v2 / DenseNet121 / EfficientNet 等の転移学習は、凝集体の「良/不良」分類にも適用可能。
- 時系列: RNN/LSTM は径トレンド予測に利用可能。

**iPSC 凝集体固有の課題**:

- **Confluency は使えない**: 2D 接着培養の占有面積指標は浮遊凝集体には不適合。
- **重なりと遮蔽**: 高密度懸濁液では凝集体同士が重なり、個別セグメンテーションが困難。
- **内部構造の可視化**: 明視野/位相差では内部壊死コアの検出に限界。OCT や DHM が候補だが iPSC 実証は未確定。
- **正解ラベルの取得コスト**: OCT4 等の免疫染色・FACS は offline で高コスト。学習データ構築がボトルネック。
- **細胞株間汎化**: 形態は培地・株によって大きく異なる（Gursky 2023 レビュー）。施設間汎化は未保証。

### 5.3 信頼性と未確定

- **現在の信頼性**: 2D/organoid であれば画像からの分化予測は AUC 0.91、accuracy 0.84–0.95 程度の報告がある。〔事実〕
- **iPSC 浮遊凝集体での信頼性**: **未確定**。代理指標として採用する場合、最低でも数十〜数百バッチの offline 正解ラベルと照合が必要。〔推定〕
- **推奨アプローチ**: まず「凝集体径・形態の定量化（教師なし/ルールベース）」を v1 で導入し、DL 品質代理指標は v2 以降の拡張とする。

---

## 6. 2D 画像解析技術の凝集体解析への転移

### 6.1 転移不能な要素

- **Confluency**: 浮遊凝集体では培養面が存在しないため適用不可。
- **コロニー境界**: 2D コロニーの「平らで均一なエッジ」は凝集体では球面/厚みを持つため、セグメンテーション手法を再学習・再設計する必要がある。

### 6.2 転移可能な要素

| 2D 技術 | 凝集体への転移 | 備考 |
|---|---|---|
| コロニー形態分類（morphcls） | 凝集体形態分類（良/不良/分化疑い） | 教師ラベルと特徴量を再定義 |
| 分化領域検出（diffdet） | 凝集体内部の不均一/壊死領域検出 | 3D 内部構造の可視化が必要 |
| 増殖曲線予測（growth） | 凝集体径トレンド予測 | 時系列回帰として転移可能 |
| DL モデル（dlmodel） | U-Net/CNN 系を凝集体画像で fine-tune | 画像ドメインの違いが大きいため再学習必須 |

---

## 7. auto_cell A 層設計への含意

### 7.1 L0–L3 分離との整合（ADR-0001）

- **L1 決定的レシピ/ルール**: 凝集体径は `aggregate_diameter_um` として analog channel 経由で取得。`cpp_aggregate_diameter` の 150–350 µm 包絡線を超えた場合、`aggregate_out_of_range` イベントを発生させ、撹拌変更または passage 検討とする。〔設計選択〕
- **L2 BO**: 画像由来の品質代理指標（径分布の尖度、平均径、円形度等）を run 単位の目的関数項に組み込む。ただし v1 では offline 正解ラベルとの対応構築が先決。〔推定〕
- **L3 LLM**: 画像異常（例：凝集体形状の急変、二峰分布の出現）の曖昧解釈・HMI 提示に限定。Critical な passage 判断は L1 の決定論的ルールに任せる。〔設計選択〕

### 7.2 観測性スタック更新

`kg_to_auto_cell.md` §4.2 の観測性スタックに追加：

| 層 | 計測 | 用途 | v1 優先度 |
|---|---|---|---|
| L1 | at-line 凝集体画像（明視野/位相差） | 径・形態トレンド、passage 判断 | 必須 |
| L1 | FBRM CLD | 連続トレンド（校正あり） | オプション |
| L1/L2 | DHM / Ovizio | 連続計測（予算・実証許容なら） | 後段 |
| L2 | DL 品質代理指標 | BO 目的関数項 | 後段 |

### 7.3 技術統制・監査

- 画像解析モデルの**バージョニング**、**教師ラベル出典**、**性能メトリクス**を記録（ALCOA-lite）。
- DL 品質代理指標の予測値は「推定」として扱い、BO 目的関数や passage トリガに組み込む際は Human-on-the-loop 承認を必須とする。〔推定：GAMP5 AI/ML Appendix D11〕

---

## 8. Human-on-the-loop との関係

- **包絡線内**: 凝集体径が 150–350 µm 内で推移する場合、L1 は自律的に撹拌や灌流を調整。
- **包絡線外/異常**: 径の急増、二峰分布、DL 品質代理指標の低信頼度予測時は、`trigger_passage` または `set_agitation_rpm` の変更を承認要求へエスカレーション。
- **DL 代理指標の信頼度**: モデルの予測不確実性（エントロピー、MC dropout 分散、OOD 検出）を可視化し、閾値超過時は人の判断を仰ぐ。〔推定〕

---

## 9. 未確定事項・次のステップ

| # | 項目 | 理由 | 次ステップ |
|---|---|---|---|
| U1 | iPSC 凝集体画像の DL 品質代理指標精度 | iPSC 浮遊凝集体に特化した実証が少ない | 自前データセット構築（OCT4/SSEA4 正解ラベル） |
| U2 | 各画像技術の iPSC 校正曲線 | DHM/FBRM/FlowCam の iPSC 固有の光散乱特性 | ベンダ資料＋実験校正 |
| U3 | 凝集体径の細胞株依存性 | 設計値 150–350 µm は初期仮説 | 複数株で分布と品質の相関調査 |
| U4 | 2D 画像解析モデルの凝集体転移効率 | ドメインギャップが大きい | 転移学習実験・データ拡張戦略 |
| U5 | DL 品質指標の BO 目的関数重み | 代理指標の信頼性が未確定 | 研究者ヒアリング＋感度分析 |

---

## 10. 出典

| ID | タイトル | URL/DOI/PMID/PMCID | 確度 |
|---|---|---|---|
| src_borys | Borys et al. 2021, Stem Cell Res Ther 12:55（Vertical-Wheel hiPSC 撹拌最適化） | DOI 10.1186/s13287-020-02109-4; PMCID PMC7805206 | 事実 |
| src_eppendorf_485 | Eppendorf App Note 485: hiPSC Aggregate Expansion in Stirred-tank Bioreactors | https://www.eppendorf.com/product-media/doc/en/11804882/... | 事実 |
| src_stemcell_mtesr3d | StemCell Technologies, Expansion of hPSCs as Aggregates in Suspension Culture Using mTeSR 3D | https://cdn.stemcell.com/media/files/manual/10000005520-... | 事実 |
| src_kropp_2019 | Kropp/Lipsitz et al. 2019, Sci Rep — at-line bypass imaging of hiPSC aggregates | DOI 10.1038/s41598-019-48814-w | 事実 |
| src_ovizio_ilinef | Ovizio iLINE-F PRO / BioProcess Online commercial partnership | https://www.bioprocessonline.com/doc/ovizio-imaging-systems-is-entering-into-a-commercial-partnership-with-merck-to-promote-its-iline-f-pro-solution-for-the-cell-gene-therapy-market-0001 | 事実 |
| src_fbrm_g400 | Mettler Toledo ParticleTrack with FBRM technology | https://www.mt.com/my/en/home/products/L1_AutochemProducts/particle-size-analyzers/particletrack-fbrm.html | 事実 |
| src_flowcam | FlowCam — What is FlowCam? | https://www.fluidimaging.com/blog/what-is-the-flowcam | 事実 |
| src_chu_2023 | Chu et al. 2023, Comput Methods Programs Biomed 229:107264 | DOI 10.1016/j.cmpb.2022.107264 | 事実 |
| src_park_2022 | Park et al. 2022, Deep learning predicts kidney organoid differentiation | 10.23876/j.krcp.22.017 | 事実 |
| src_piotrowski_2021 | Piotrowski et al. 2021, Comput Biol Med 129:104172 | DOI 10.1016/j.compbiomed.2020.104172 | 事実 |
| src_waisman_2019 | Waisman et al. 2019, Stem Cell Rep 12:845–859 | DOI 10.1016/j.stemcr.2019.02.004 | 事実 |
| src_maddah_2014 | Maddah et al. 2014, J Lab Autom 19:454–460 | DOI 10.1177/2211068214529287 | 事実 |
| src_kato_2016 | Kato et al. 2016, Sci Rep 6:34009 | DOI 10.1038/srep34009 | 事実 |
| src_gursky_2023 | Gursky 2023, How Morphology of hPSCs Determines Clone Selection（IntechOpen） | https://www.intechopen.com/online-first/87934 | 事実 |
| src_manstein_2021 | Manstein & Zweigerdt 2021（plant_model 原典） | DOI 10.1002/sctm.20-0453; PMCID PMC8666714 | 事実 |
| ADR-0001 | Control architecture — thin LLM orchestrator over deterministic tools + Bayesian optimization | docs/design/adr/0001-control-architecture.md | 事実 |
| requirements | auto_cell A 層 制御システム 要求仕様 | docs/design/requirements.md | 事実 |

---

*本レポートは A 層（iPSC 浮遊/凝集体バイオリアクター制御）に限定。樹立/分化/双腕/接着 conf は設計境界。*
