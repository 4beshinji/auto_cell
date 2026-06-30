# S05: iPSC 浮遊凝集体の at-line/in-line 画像解析と DL 品質代理指標調査

> **担当**: 画像解析・機械学習調査エージェント  
> **Scope**: auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御、Manstein 型灌流 0→7 vvd）  
> **Date**: 2026-06-30  
> **前提**: ADR-0001、`docs/design/kg_to_auto_cell.md` §4.2/§7.1、`docs/design/ground_knowledge/additional_aggregate_imaging.md`、`docs/design/ground_knowledge/additional_investigation_integrated.md` §7

---

## 1. Executive Summary

1. **v1 で現実的な画像計測は at-line 明視野/位相差**: in-line DHM/FBRM は技術的に存在するが、iPSC 浮遊凝集体（150–350 µm）の turn-key 実証・校正は限定的。〔事実：Borys 2021; Schwedhelm 2019; Ovizio ベンダ資料〕
2. **凝集体径・形態は品質と相関**: 径 >300 µm で OCT4 発現低下、>400 µm で拡散制限による壊死/未分化性低下リスクが報告されている。〔事実：Borys 2021; escholarship 学位論文; StemCell mTeSR 3D マニュアル〕
3. **label-free DL 品質代理指標は 2D iPSC で高い相関が示されている**: Akiyoshi 2024 は明視野画像から OCT4/NANOG を r≈0.998/0.978 で予測。ただし **浮遊凝集体への直接適用は未確定**。〔事実：Akiyoshi 2024; 推定：浮遊凝集体への転移〕
4. **セグメンテーションは DL が古典手法を上回る**: 明視野スフェロイド/オルガノイドでは Mask R-CNN・U-Net が Otsu/watershed を上回り、特に照明変化・接触・形態多様性に頑健。〔事実：Grexa 2021; Oudouar 2025〕
5. **BO 目的関数への統合は段階的に**: v1 では画像由来の径分布・形態メトリクスを L1 イベント/監視入力とし、Phase 2 以降、offline 正解ラベル（OCT4/SOX2/NANOG/SSEA4/TRA-1-60）で検証された DL 代理指標を品質項に追加する。〔推定：設計判断〕
6. **Human-on-the-loop は必須**: DL 代理指標の予測不確実性（MC dropout / ensemble / OOD）が閾値を超えた場合、研究者承認にエスカレーションする。〔設計判断：ADR-0001; Annex 22 推定〕

---

## 2. 画像技術比較表

| 技術 | 計測原理 | 配置 | iPSC 実証 | v1 位置づけ | コスト感・留保 |
|---|---|---|---|---|---|
| **DHM / Ovizio iLINE-F PRO** | D3HM/位相画像、ラベルフリー | in-line（バイオリアクタ接続） | 懸浮細胞・MSC・CAR-T・T 細胞で VCD/viability/形態実証。iPSC 凝集体（>150 µm）の turn-key 実証は限定〔推定〕 | オプション〜後段 | 高〜中（装置 + 使い捨て BioConnect）。OPC UA 対応、cGMP/21 CFR Part 11 ready〔事実〕 |
| **FBRM / ParticleTrack** | 回転レーザー後方散乱 → CLD | in-line（プローブ） | 結晶化・凝集プロセスで広く使用。iPSC 凝集体直接適用例は少ない〔推定〕 | トレンド監視（画像法で校正） | 中。CLD は真の粒径分布ではなく、球形・透光性凝集体への換算誤差〔事実〕 |
| **FlowCam** | フローイメージング顕微鏡（明視野＋蛍光 option） | at-line / offline | 海洋微生物・粒子解析で実績。iPSC 凝集体報告は少ない〔推定〕 | 日次 at-line | 中。高濃度・重なり凝集体では計数漏れ。VisualAI™ 分類あり〔事実〕 |
| **明視野/位相差 at-line** | 光学顕微鏡＋画像解析 | at-line（サンプリングまたは bypass） | **iPSC 浮遊凝集体で最も一般的**。Kropp 2019 / Schwedhelm 2019 の bypass 顕微鏡方式あり〔事実〕 | **v1 必須** | 低〜中（既存顕微鏡＋自動撮影）。人の主観・サンプリングバイアスあり〔事実〕 |

### 2.1 各技術の詳細と設計含意

#### DHM / Ovizio iLINE-F PRO
- **原理**: Double Differential Digital Holographic Microscopy（D3HM）。細胞の位相シフトを数値再構成し、ラベルフリーで 3D トポグラフィを取得。〔事実：Ovizio ベンダ資料〕
- **性能**: 細胞径 2–100 µm、細胞密度 1×10⁵–2×10⁷ cells/mL を謳う。〔事実：Semantics Scholar PDF 引用〕
- **iPSC 凝集体への留保**: 150–350 µm の凝集体は個別細胞・小クランプの範囲を超え、内部までの位相解析は光の多重散乱により難しい。表層形態・サイズ分布・クラスタ数が主な出力となると推定。〔推定〕
- **LADS/OPC UA**: OPC UA 対応で Scada/DeltaV 連接可能。cGMP/21 CFR Part 11 ready。〔事実：BioProcess Online; ChemoMetec〕
- **設計位置づけ**: v1 では「予算・実証許容なら導入」オプション。凝集体径の analog channel としては at-line 画像または FBRM プロキシが現実的。

#### FBRM / ParticleTrack
- **原理**: サファイア窓先端で焦点を合わせたレーザーが高速回転（~2 m/s）。粒子通過時の後方散乱パルス持続時間 × 走査速度 = chord length。〔事実：Mettler Toledo〕
- **iPSC 凝集体への留保**: 凝集体は球形ではなく透光性が高いため、CLD からの径換算は非自明。Square-weighted CLD で大粒子感度を上げるが、絶対径は画像法で補正する必要あり。〔事実：Chow et al. 2008; 各種 FBRM 論文〕
- **設計位置づけ**: CLD トレンド監視は有用だが、v1 の passage トリガには**画像法で校正済みの径**を用いる。

#### FlowCam
- **原理**: サンプルを流路で撮影し、個別粒子画像からサイズ・形態を解析。2 µm–1 mm（機種依存）。〔事実：FlowCam 資料〕
- **iPSC 凝集体**: 高濃度培養液では凝集体同士の重なり・破砕が生じやすく、自動計数の信頼性は濃度依存。日次 at-line 運用を想定。〔推定〕
- **設計位置づけ**: 日次 at-line 品質チェックに適する。iPSC 固有の分類ライブラリ構築が必要。

#### 明視野/位相差 at-line
- **実例**: Eppendorf App Note 485 では 1 L DASGIP Spinner Vessel で hiPSC を 5 日間培養し、毎日 20 mL サンプルを採取、ImageJ で 20 個の凝集体径を手動測定。〔事実：Eppendorf AN485〕
- **自動化**: Kropp et al. 2019（Sci Rep）の bypass 顕微鏡方式、Schwedhelm 2019 の incubator 内 in-flow imaging（15 mL/min、2 min / 24 h、~2000 個カウント）が先例。〔事実：Kropp 2019; Schwedhelm 2019〕
- **設計位置づけ**: v1 必須。LADS sensor Function として `aggregate_diameter_um` を analog channel 経由で取得する前提（`kg_to_auto_cell.md` §4.2 と整合）。

---

## 3. 自動セグメンテーション手法比較

### 3.1 手法マトリクス

| 手法 | アーキテクチャ | 強み | 弱み | 凝集体適合性 | 実装例 |
|---|---|---|---|---|---|
| **Otsu + Watershed** | 古典画像処理 | 高速、説明可能 | 照明変化・接触・形態多様性に弱い | 低〜中（前処理で補強可） | ImageJ、scikit-image |
| **U-Net** | エンコーダー・デコーダー CNN | ピクセル精度高い、少数データでも fine-tune 可能 | インスタンス分割・重なりに弱い | 高（均一背景・非接触凝集体） | PyTorch/TensorFlow、segmentation-models-pytorch |
| **Mask R-CNN** | 検出 + インスタンスセグメンテーション | 重なり対象の個別検出・分類が可能 | 計算コスト高、アノテーション多め | 高（高密度・接触凝集体） | detectron2、mmdetection |
| **StarDist** | 星型凸オブジェクト向け CNN | 少数アノテーション（20–50 画像）で fine-tune 可能、 nuclei に強い | 星型凸以外の形状（変形凝集体）に弱い | 中（球形凝集体には有効） | stardist (Python) |
| **Cellpose** | 一般細胞セグメンテーション | 明視野/位相差 label-free に強い、直径指定でロバスト | 非常に大きな凝集体・厚みは学習が必要 | 高（bypass 明視野に推奨） | cellpose (Python) |
| **SAM / Cellpose-SAM** | セグメンテーション foundation model | 未知モダリティのフォールバック | 全対象を同じに扱う、プロンプト戦略が必要 | 中（標準化後の補助） | segment-anything、cellpose 3.0 |

### 3.2 実証データ

- **Grexa 2021（PMC8292460）**: 981 枚の明視野スフェロイド画像で U-Net と Mask R-CNN を比較。古典手法（Otsu/watershed）は照明条件・形態多様性・接触に敏感。DL 手法は再パラメータ化なしでロバストに検出。Mask R-CNN は IoU 0.5–0.85 で平均 precision/sensitivity が U-Net を上回り、U-Net は IoU 0.9–0.95 でピクセル精度が勝る。〔事実〕
- **Oudouar 2025**: 3D スフェロイド分割で U-Net、HRNet、DeepLabV3+ を比較。HRNet-Seg が Jaccard 0.9512（validation）を達成。〔事実〕
- **Cellpose-SAM**: Label-free phase contrast では Cellpose-SAM livecell variant が推奨。StarDist は非凸細胞には不向き。〔推定：SciRouter 2026〕

### 3.3 設計推奨

| 用途 | 推奨手法 | 理由 |
|---|---|---|
| v1 迅速立ち上げ | Cellpose（cyto2/cyto3）+ 手動補正 | 明視野/位相差に汎用性高し、追加学習不要で開始可能 |
| 高精度インスタンス分割 | Mask R-CNN | 凝集体接触・重なりへの対応 |
| 少数アノテーション・球形対象 | StarDist | 20–50 枚で fine-tune 可能 |
| ルールベース・高速 | Otsu + Watershed + 品質フィルタ | 計算コスト低、説明可能 |

---

## 4. 品質代理指標の構築手法

### 4.1 画像特徴量（ルールベース）

iPSC 浮遊凝集体の品質代理指標として抽出可能な基本特徴量：

- **サイズ**: 面積、等価直径、最大/最小径、フェレ径
- **形状**: 円形度（circularity）、アスペクト比、細長さ、輪郭の粗さ、凸性
- **内部構造**: 位相差画像での内部輝度勾配、質感（GLCM ハラリック特徴）、壊死コアのシグナル低下
- **分布**: サイズ分布の平均、標準偏差、尖度、歪度、ピーク数（一峰性/二峰性）、大径割合（>350 µm、>400 µm）
- **濃度**: 画像内凝集体数、占有率（凝集体が画像を占める割合 = confluency の凝集体版）

### 4.2 DL 品質代理指標

#### 教師あり回帰/分類
- **入力**: 明視野/位相差画像（FOV 全体または個別凝集体パッチ）
- **出力**: OCT4/SOX2/NANOG/SSEA4/TRA-1-60 陽性率、good/fair/poor 分類、分化疑いフラグ
- **アーキテクチャ**: ResNet50v2 / DenseNet121 / EfficientNet + 回帰ヘッド。ImageNet pretrain → fine-tune。〔推定：Akiyoshi 2024; organoid 転移学習例〕

#### 教師なし/半教師あり異常検知
- **One-class SVM / Isolation Forest**: 正常凝集体画像の分布から外れた画像を異常とみなす。
- **UMAP + One-class SVM**: Akiyoshi 2024 が採用。明視野画像を UMAP で 3次元に射影し、one-class SVM で pluripotency スコアを算出。〔事実：Akiyoshi 2024〕
- **Autoencoder / VAE**: 再構成誤差が大きい画像を異常（分化・壊死疑い）とする。

### 4.3 2D 画像解析モデルから凝集体解析への転移

**転移できない要素**:
- **Confluency**: 2D 接着培養の占有面積指標は、浮遊凝集体には存在しない。〔事実〕
- **コロニー境界**: 2D コロニーの「平らで均一なエッジ」は凝集体では球面/厚みを持つため、セグメンテーション手法を再学習・再設計する必要がある。〔推定〕

**転移できる要素**:
- **エンコーダー重み**: ImageNet pretrain または live-cell データセット pretrain（Cellpose cyto3 等）を凝集体画像で fine-tune。
- **分類ヘッド**: 2D iPSC 品質分類器の最終層を、凝集体画像パッチの「良好/不良/分化疑い」分類に置き換え。
- **データ拡張**: 回転、スケール、コントラスト、ぼかし、擬似重なり合成（Poisson blending 等）で凝集体固有のばらつきを増強。
- **教師ラベル**: OCT4/SOX2/NANOG/SSEA4/TRA-1-60 の run 単位陽性率を画像パッチ単位にマッピング（弱教師あり学習）することでアノテーションコストを抑制。〔推定〕

**課題**:
- **ドメインギャップ**: 2D コロニーと 3D 凝集体では外観が大きく異なる。再学習が必須。
- **重なりと遮蔽**: 高密度懸濁液では凝集体同士が重なり、個別セグメンテーションが困難。
- **内部構造の可視化**: 明視野/位相差では内部壊死コアの検出に限界。DHM/OCT が候補だが iPSC 実証は未確定。
- **細胞株間汎化**: 形態は培地・株によって大きく異なる（Gursky 2023）。施設間汎化は未保証。〔事実：Gursky 2023; Akiyoshi 2024〕

### 4.4 先行研究の性能

| 研究 | 対象 | 手法 | 性能 | 出典 |
|---|---|---|---|---|
| Akiyoshi 2024 | 2D hiPSC 明視野 | UMAP + One-class SVM / ResNet50 | OCT4 予測 r=0.998、NANOG r=0.978、FCM との相関 r=0.91 | PMC11231322 |
| Waisman 2019 | mESC 分化開始早期 | DL | 非常早期の分化を高精度に予測 | Stem Cell Rep 12:845–859 |
| Maddah 2014 | iPSC コロニー品質 | time-lapse + 形態特徴量 | good/fair/poor 分類 accuracy 0.80–0.89 | J Lab Autom 19:454–460 |
| Park 2022 | kidney organoid 分化 | DenseNet121 転移学習 | qPCR 発現予測 PCC 0.783 | 10.23876/j.krcp.22.017 |
| Organoid retinal differentiation | マウス ESC オルガノイド明視野 | ResNet50v2 転移学習 | ROC-AUC 0.91 | ResearchGate 364238541 |
| Coronnello 2021 レビュー | iPSC 画像ベース品質 | CNN/SVM/伝統的 ML | 精度 82.5–92.7% | PMC8930923 |

> ⚠️ 上記の高い性能は **2D 培養または organoid** におけるもの。iPSC **浮遊凝集体**に特化した label-free DL 品質代理指標の実証は、本調査で確認した限り乏しく、未確定である。

---

## 5. 画像特徴量と offline QC ラベルの対応

### 5.1 凝集体径と pluripotency マーカー

| 主張 | 根拠 | 確度 |
|---|---|---|
| 凝集体径 150–350 µm が A 層目標範囲 | `kg_to_auto_cell.md` §4; Borys 2021（Vertical-Wheel day 5 で 169–275 µm） | 事実/設計選択 |
| 径 >300 µm で OCT4 発現が低下する傾向 | escholarship 学位論文（Fig 4.5） | 事実（hPSC） |
| 径 >400 µm で壊死/未分化性低下のリスク | Borys 2021; StemCell mTeSR 3D マニュアル | 事実 |
| 細胞株・培地・撹拌によって最適径は変動 | Eppendorf AN485; Borys 2021 | 事実 |
| auto_cell の 150–350 µm は初期仮説であり再校正が必要 | 設計判断 | 未確定→推定 |

### 5.2 明視野画像と分子マーカーの対応

| 主張 | 根拠 | 確度 |
|---|---|---|
| 2D hiPSC 明視野画像から OCT4/NANOG を高相関で予測可能 | Akiyoshi 2024（r=0.998/0.978） | 事実 |
| 異なる細胞株間では汎化が困難（相関係数 -0.71〜0.79） | Akiyoshi 2024（1231A3, ND50018, ND50019） | 事実 |
| 浮遊凝集体画像から OCT4/SOX2/NANOG/SSEA4/TRA-1-60 を予測できるか | 未確認 | 未確定 |
| 画像代理指標と offline QC の対応には数十〜数百バッチの正解ラベルが必要 | 推定 | 推定 |

### 5.3 品質マーカーと BO 目的関数での扱い

`kg_to_auto_cell.md` §4.3 に基づく統合方針：

| 読み出し | 測定 | BO での扱い |
|---|---|---|
| 収量（VCD/fold） | capacitance/計数 | 目的項（連続） |
| 生存率 | Nova FLEX2/画像 | 目的項（連続%） |
| 多能性 % 陽性（OCT4/SOX2/NANOG/SSEA4/TRA-1-60） | フローサイト/免疫染色 | 目的項（連続%）または pass/fail ゲート |
| ラベルフリー画像代理 | 明視野/DHM＋DL | 未確定 → 検証後に目的項へ昇格 |
| 同一性・核型/CNV | offline 多日 | 制約/ゲート |
| 自発分化・三胚葉分化能 | qPCR/EB 形成 | offline 事後/cadence |

---

## 6. DL 不確実性と HITL エスカレーション設計

### 6.1 不確実性定量化手法

| 手法 | 種類 | 長所 | 短所 | 推奨度 |
|---|---|---|---|---|
| **MC Dropout** | 認識論的不確実性（epistemic） | 追加コスト少、実装容易 | dropout 率・回数が主観的、校正必要 | 中 |
| **Deep Ensemble** | 認識論的不確実性 | 実装が直感的、分布多様性を捉えやすい | 計算コスト、過大/過小評価リスク | 高 |
| **予測エントロピー** | 全不確実性 | OOD 検出に高い AUROC を示すことが多い | データノイズとモデル不確実性が混在 | 高 |
| **BALD** | 認識論的不確実性 | Active learning にも使える | データセット依存で変動 | 中 |
| **Mahalanobis 距離 / 特徴量空間距離** | OOD 検出 | 教師なしで実装可能 | 分布仮定（多変量正規）が必要 | 中 |
| **Input reconstruction error（AE/VAE）** | OOD 検出 | 教師なし | 高次元・複雑画像では再構成が困難 | 低〜中 |

### 6.2 エスカレーション設計

```
画像取得 → 前処理 → セグメンテーション → 特徴量抽出 → DL 品質予測
                                                ↓
                                        [不確実性計算]
                                                ↓
                    ┌───────────────────────────┼───────────────────────────┐
                    ↓                           ↓                           ↓
              信頼度高                   中程度の不確実性              高不確実性/OOD
                    ↓                           ↓                           ↓
              L1/L2 に自動入力          HMI に黄色警告表示          研究者承認へエスカレーション
              （イベント/BO項）        （参考値として提示）        （赤警告、操作保留）
```

### 6.3 閾値設計（初期仮説）

| 指標 | 低信頼（エスカレーション） | 備考 |
|---|---|---|
| 予測エントロピー | 上位 5% タイル | 校正後に再設定 |
| MC dropout 標準偏差 | 予測値の 20% 以上 | 回帰の場合 |
| Deep ensemble 標準偏差 | 予測値の 15% 以上 | 回帰の場合 |
| Mahalanobis 距離 | 訓練分布の 95% 信頼楕円外 | OOD 検出 |
| 入力画像品質 | ピント外れ・過曝・欠損 | 前処理段階で棄却 |

> 上記閾値は **未確定**。実データでの感度分析と研究者ヒアリングが必要。

---

## 7. BO 目的関数統合方針

### 7.1 段階的統合ロードマップ

| フェーズ | 画像情報の使い方 | BO 目的関数 | HITL |
|---|---|---|---|
| **v1 / Phase 1** | at-line 画像から凝集体径・形態メトリクスを算出。L1 イベント（`aggregate_out_of_range`、`large_aggregate_high`）と監視トレンドに使用。 | `J = yield × viability × pluripotency%`（offline QC 必須）。画像代理指標は **含めない**。 | 包絡線外 setpoint・trigger_passage を承認。 |
| **Phase 2** | 画像特徴量（平均径、標準偏差、円形度、大径割合）を run 単位スカラに集約し、BO 目的関数の追加項として統合（検証後）。 | `J = yield × viability × pluripotency% × aggregate_quality_score` | BO 提案を承認。画像特徴量の異常値は警告。 |
| **Phase 3** | DL 品質代理指標（OCT4/SOX2 予測等）を BO 品質項に統合。 | `J = yield × viability × pluripotency% × dl_quality_proxy`（重みは感度分析） | 低信頼度 DL 予測時はエスカレーション。 |

### 7.2 品質項の数式例（推定）

```
aggregate_quality_score = w_size × size_score + w_shape × shape_score + w_distribution × distribution_score

J_run = (VCD_fold × viability) × pluripotency_pct × aggregate_quality_score × cost_penalty
```

- `size_score`: 平均径が目標範囲（150–350 µm）内で最大、外れると減衰
- `shape_score`: 円形度・平滑度の加重平均
- `distribution_score`: 一峰性・均一性を獎励、二峰性・大径割合をペナルティ
- `cost_penalty`: 培地・時間コスト（Phase 3）

### 7.3 Safe/Constrained BO との整合

- `kg_to_auto_cell.md` §4.3 で示す通り、同一性・核型・無菌性は **pass/fail 制約**として扱う。
- 画像代理指標は **連続目的項**として統合し、閾値超過時は HITL エスカレーション。
- BO の獲得関数は Expected Improvement（EI）または Noisy Expected Improvement（NEI）を使用。画像由来のノイズを考慮する場合は NEI/qNEI が適切。〔推定：Siska 2026; UGent BO 論文〕

---

## 7.4 画像取得 cadence（連続 vs 日次）と L1 イベント設計の整合

| cadence | 取得方法 | 用途 | L1 イベントとの整合 |
|---|---|---|---|
| **連続/準連続** | DHM/Ovizio（in-line）、bypass 顕微鏡（15 mL/min × 2 min / 24 h 等） | トレンド監視、異常検知 | 即時イベントは発火せず、**移動平均・レート制限**した上で `aggregate_out_of_range` を検討。連続値として `aggregate_diameter_um` analog channel に書き込む。〔推定〕 |
| **日次** | FlowCam、手動サンプリング＋顕微鏡 | run 単位の品質評価、BO 入力 | 日次画像解析結果を **次サイクルの L1 しきい値調整**または **BO 目的関数項**に使用。L1 即時制御には使わない。〔設計判断〕 |
| **条件起動** | 異常トリガ時（乳酸高値、DO 低値、操作者入力）に追加撮影 | 原因特定、HITL 判断材料 | `lactate_high` 等のイベント発生時に `take_sample` → 画像取得を連動させ、研究者への追加情報とする。〔推定〕 |

### 7.5 設計上の注意

- L1 決定的レシピは **連続センサ（pH/DO/glucose/lactate/VCD）を主トリガ**とし、画像は **日次/条件起動の二次情報**として位置づける。画像取得の遅延（数分〜数時間）を許容する。〔設計判断〕
- `aggregate_out_of_range` イベントは、**最新の画像解析結果**または **FBRM 等の連続プロキシ**を使って発火。画像が古い場合は信頼度スコアを下げ、HMI に「データ鮮度」警告を表示。〔推定〕
- Phase 2 以降、画像特徴量の run 単位スカラを BO にフィードバックする際は、cadence を「run 終了時」に揃え、run 内の即時制御ループには組み込まない。〔設計判断〕

---

## 8. 実装方針（Python ライブラリ）

### 8.1 推奨技術スタック

| 層 | ライブラリ | 用途 |
|---|---|---|
| 画像 I/O・前処理 | OpenCV, Pillow, imageio | 読み込み、リサイズ、正規化、Z-stack 投影 |
| 古典画像解析 | scikit-image, scipy.ndimage | 閾値処理、watershed、形態学、ラベリング、特徴量抽出 |
| DL セグメンテーション | cellpose, stardist, segmentation-models-pytorch, detectron2 | U-Net/Mask R-CNN/Cellpose/StarDist |
| DL 分類/回帰 | PyTorch, torchvision, timm | ResNet/EfficientNet fine-tune |
| 不確実性 | PyTorch + カスタム実装（MC dropout/ensemble） | エントロピー、BALD、OOD 検出 |
| 特徴量・統計 | pandas, numpy, scipy | サイズ分布、相関分析 |
| 可視化 | matplotlib, seaborn, napari | 画像・マスク・トレンド表示 |
| BO | BoTorch, Ax | GP サーロゲート、獲得関数 |
| ワークフロー | prefect/dagster または単純な Python スクリプト | 画像取得→解析→通知 |

### 8.2 画像解析パイプライン概略

```python
# 概念実装（参考）
from pathlib import Path
import cv2
import numpy as np
from cellpose import models
from skimage import measure

class AggregateImagePipeline:
    def __init__(self, segmentation_model="cellpose", device="cpu"):
        if segmentation_model == "cellpose":
            self.model = models.CellposeModel(gpu=(device=="cuda"), model_type="cyto3")
        # StarDist/Mask R-CNN 分岐も同様

    def preprocess(self, img: np.ndarray) -> np.ndarray:
        # Z-stack 投影、コントラスト正規化、リサイズ
        return normalize_zstack(img)

    def segment(self, img: np.ndarray, diameter_um: float = 200):
        masks, flows, styles = self.model.eval(img, diameter=diameter_um, channels=[0,0])
        return masks

    def extract_features(self, masks: np.ndarray, pixel_size_um: float) -> pd.DataFrame:
        props = measure.regionprops_table(
            masks,
            properties=["label", "area", "equivalent_diameter", "perimeter",
                        "solidity", "eccentricity", "major_axis_length", "minor_axis_length"]
        )
        df = pd.DataFrame(props)
        df["diameter_um"] = df["equivalent_diameter"] * pixel_size_um
        df["circularity"] = 4 * np.pi * df["area"] / (df["perimeter"] ** 2)
        return df

    def quality_proxy(self, img: np.ndarray, masks: np.ndarray) -> dict:
        # ルールベーススコア
        features = self.extract_features(masks, pixel_size_um=1.5)
        score = compute_aggregate_quality_score(features)  # 設計項に応じて実装
        return {"features": features, "quality_score": score}
```

### 8.3 データフロー

```
バイオリアクター / サンプリングロボ
        │
        ▼
┌─────────────────┐
│ 画像取得デバイス │  ← 明視野/位相差顕微鏡、FlowCam、DHM、FBRM
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   前処理層       │  ← Z-stack 投影、コントラスト正規化、ノイズ除去
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  セグメンテーション │  ← Cellpose/StarDist/Mask R-CNN/U-Net
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  特徴量抽出      │  ← 径、面積、円形度、分布、大径割合
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐  ┌─────────────┐
│ L1 イベント │  │ DL 品質代理指標 │
│ 判定     │  │ （Phase 2〜）  │
└────┬───┘  └──────┬──────┘
     │             │
     ▼             ▼
┌─────────────────────────┐
│    BO 目的関数 / HMI      │
│  （不確実性に応じて HITL） │
└─────────────────────────┘
```

### 8.4 ALCOA-lite / 規制対応

- 画像解析モデルは **バージョン管理**（DVC または git-lfs）。
- 教師ラベルは `event_store` と紐付け、誰・いつ・何をで追跡可能に。
- DL 予測値は「推定」として扱い、L1 クリティカル制御には直接使用しない（ADR-0001）。
- 静的決定論的証明：固定シード・固定重み・再現性テストを CI に組み込む。

---

## 9. 未確定事項と実験計画

| # | 未確定事項 | 理由 | 次ステップ | 目標時期 |
|---|---|---|---|---|
| U1 | iPSC 浮遊凝集体画像から OCT4/SOX2/NANOG/SSEA4/TRA-1-60 を予測できるか | 浮遊凝集体への特化実証が乏しい | 自前データセット構築（offline 正解ラベル付き） | Phase 2 |
| U2 | 各画像技術の iPSC 校正曲線 | DHM/FBRM/FlowCam の iPSC 固有の光散乱特性 | ベンダ PoC + 実験校正（画像法 vs offline 計数） | v1〜Phase 2 |
| U3 | 凝集体径の細胞株依存性 | 150–350 µm は初期仮説 | 複数株で分布と品質の相関調査 | v1 |
| U4 | 2D 画像解析モデルの凝集体転移効率 | ドメインギャップ（confluency → aggregate） | Cellpose/StarDist の転移学習実験、データ拡張戦略 | Phase 2 |
| U5 | DL 品質指標の BO 目的関数重み | 代理指標の信頼性が未確定 | 研究者ヒアリング＋感度分析＋多目的 BO | Phase 2〜3 |
| U6 | 不確実性閾値の妥当性 | エスカレーション過剰/過少を避ける必要 | 感度分析、擬似 OOD データでの AUROC 検証 | Phase 2 |
| U7 | 画像取得 cadence（連続 vs 日次）と L1 イベントの整合 | 画像は日次が現実的、L1 は連続トリガを前提 | 日次画像 + トリガ時追加撮影のハイブリッド設計 | v1 |
| U8 | Annex 22 下での DL 画像解析モデルの分類 | 静的決定論的モデルとして扱えるか | Intended Use 文書化、規制コンサル | Phase 2 |

### 9.1 推奨実験計画（v1 → Phase 2）

1. **v1 基準画像データセット**: 各 run で at-line 明視野/位相差画像を取得。同時に Nova FLEX2/ChemoMetec で VCD/viability、offline で凝集体径（ImageJ 等）を取得。
2. **画像法 vs offline 径の相関**: Pearson/Spearman 相関、Bland-Altman 解析。目標 R² ≥ 0.9。
3. **凝集体径分布と品質マーカーの相関**: 各 run の最終日に OCT4/SOX2/NANOG/SSEA4/TRA-1-60 を計測し、平均径・標準偏差・大径割合との回帰モデルを構築。
4. **セグメンテーション手法比較**: Cellpose vs StarDist vs Mask R-CNN（手動アノテション 100–300 枚）で IoU、検出率、処理速度を比較。
5. **Phase 2 DL 代理指標 PoC**: 数十 run 分の画像 + 正解ラベルで ResNet/EfficientNet fine-tune。クロスバリデーションで AUC/R² を評価。

---

## 10. 出典リスト

| ID | タイトル | URL/DOI/PMID/PMCID | 確度 |
|---|---|---|---|
| src_borys_2021 | Borys et al. 2021, Stem Cell Res Ther 12:55（Vertical-Wheel hiPSC 撹拌最適化） | DOI 10.1186/s13287-020-02109-4; PMCID PMC7805206 | 事実 |
| src_schwedhelm_2019 | Schwedhelm et al. 2019, Sci Rep — CSTR in-flow imaging of hiPSC aggregates | PMCID PMC6707254 | 事実 |
| src_kropp_2019 | Kropp/Lipsitz et al. 2019, Sci Rep — at-line bypass imaging of hiPSC aggregates | DOI 10.1038/s41598-019-48814-w | 事実 |
| src_eppendorf_485 | Eppendorf App Note 485: hiPSC Aggregate Expansion in Stirred-tank Bioreactors | https://www.eppendorf.com/product-media/doc/en/11804882/... | 事実 |
| src_stemcell_mtesr3d | StemCell Technologies, Expansion of hPSCs as Aggregates in Suspension Culture Using mTeSR 3D | https://cdn.stemcell.com/media/files/manual/10000005520-... | 事実 |
| src_ovizio_ilinef | Ovizio iLINE-F PRO / BioProcess Online commercial partnership | https://www.bioprocessonline.com/doc/ovizio-imaging-systems-is-entering-into-a-commercial-partnership-with-merck-to-promote-its-iline-f-pro-solution-for-the-cell-gene-therapy-market-0001 | 事実 |
| src_ovizio_dhm | Ovizio iLINE-F PRO Analyzer (ChemoMetec) | https://chemometec.com/fixed/ovizio-iline-f-pro-analyzer/ | 事実 |
| src_akiyoshi_2024 | Akiyoshi et al. 2024, label-free image prediction of pluripotency markers | PMCID PMC11231322 | 事実 |
| src_grexa_2021 | Grexa et al. 2021, SpheroidPicker: Mask R-CNN/U-Net spheroid segmentation | PMCID PMC8292460 | 事実 |
| src_oudouar_2025 | Oudouar et al. 2025, 3D spheroid segmentation architectures | DOI 10.3390/computers14030086 | 事実 |
| src_coronnello_2021 | Coronnello et al. 2021, ML/DL for iPSC identification and function | PMCID PMC8930923 | 事実 |
| src_lien_2023 | Lien et al. 2023, iPSC-RPE differentiation degree by CNN | DOI 10.3390/cells12020211 | 事実 |
| src_waisman_2019 | Waisman et al. 2019, early mESC differentiation prediction by DL | Stem Cell Rep 12:845–859 | 事実 |
| src_maddah_2014 | Maddah et al. 2014, iPSC colony quality classification | J Lab Autom 19:454–460 | 事実 |
| src_park_2022 | Park et al. 2022, kidney organoid differentiation by DenseNet | DOI 10.23876/j.krcp.22.017 | 事実 |
| src_piotrowski_2021 | Piotrowski et al. 2021, hPSC culture status DL segmentation | DOI 10.1016/j.compbiomed.2020.104172 | 事実 |
| src_kato_2016 | Kato et al. 2016, hPSC colony morphology and gene expression | DOI 10.1038/srep34009 | 事実 |
| src_gursky_2023 | Gursky 2023, hPSC morphology determines clone selection | https://www.intechopen.com/online-first/87934 | 事実 |
| src_manstein_2021 | Manstein & Zweigerdt 2021（plant_model 原典） | DOI 10.1002/sctm.20-0453; PMCID PMC8666714 | 事実 |
| src_siska_2026 | Siska et al. 2026, A Guide to Bayesian Optimization in Bioprocess Engineering | PMCID PMC13003447 | 事実 |
| src_ugent_bo_2025 | Bayesian cell therapy process optimization (BoTorch/qNEI) | https://backoffice.biblio.ugent.be/download/... | 事実 |
| src_ood_review_2022 | Out-of-Distribution Detection Based on Deep Learning: A Review | DOI 10.3390/electronics11213500 | 事実 |
| src_mcdropout_ensemble | Comparing Uncertainty Methods / Active Learning (GitHub) | https://github.com/Asimawad/Comparing-Uncertainty-Methods-Active-Learning | 推定 |
| src_fbrm_cld | Estimating Average Particle Size by FBRM | https://www.academia.edu/21372849/... | 事実 |
| src_fbrm_kalman | Use of a Kalman filter to reconstruct PSDs from FBRM | DOI 10.1016/j.ces.2011.07.025 | 事実 |
| src_cellpose_stardist_qupath | Segmentation with CellPose or StarDist in QuPath | https://montpellierressourcesimagerie.github.io/qupath_scripts/md_dl_sd_cp.html | 事実 |
| src_scirouter_cellpose | Cell Segmentation Models Compared: Cellpose vs StarDist vs Mesmer vs SAM | https://scirouter.ai/blog/cell-segmentation-models-compared-cellpose-stardist-mesmer/ | 推定 |
| src_cuesta_gomez_2023 | Cuesta-Gomez et al. 2023, 3D suspension improves iPSC expansion | PMCID PMC10245469 | 事実 |
| src_huang_2020 | Huang 2020, Process development and scale-up of PSC manufacturing | https://www.insights.bio/cell-and-gene-therapy-insights/journal/article/1784/ | 事実 |
| src_olmer_2012 | Olmer et al. 2012, Suspension culture of hPSCs in stirred tank | PMCID PMC3460618 | 事実 |
| src_escholarship_aggregate_size | escholarship dissertation — Reduction in OCT4 maintenance as aggregate size >300 µm | https://escholarship.org/content/qt3dh0t8f7/qt3dh0t8f7.pdf | 事実 |
| ADR-0001 | Control architecture — thin LLM orchestrator over deterministic tools + Bayesian optimization | `docs/design/adr/0001-control-architecture.md` | 事実 |

---

*本レポートは A 層（iPSC 浮遊/凝集体バイオリアクター制御）に限定。全主張には確度（事実/推定/未確定/設計判断）と出典を付与した。*
