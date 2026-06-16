# CHO から iPSC への CPP 転換・相違に関する追加調査レポート

> **担当**: CHO to iPSC CPP translation（追加調査 Agent Swarm）  
> **Mode**: A（ground knowledge 調査レポート）  
> **Date**: 2026-06-16  
> **Scope**: auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御、Manstein 型灌流 0→7 vvd）  
> **Premise**: ADR-0001（L0 局所 PID + L1 決定的レシピ/ルール + L2 ベイズ最適化 + L3 薄い LLM オーケストレータ）、Human-on-the-loop

---

## 1. エグゼクティブサマリー

フィジカルAI包括調査レポート（`/home/sin/Downloads/report/report.md`）と auto_cell A 層設計の照合分析で、**対象プロセスの相違（CHO/mAb vs iPSC 浮遊灌流）**が最大の補完ドメインとして浮上した。本レポートは、CHO 由来の CPP 制御戦略・数値を iPSC に転用する際の**代謝特性の差異**、**凝集体形成が CPP に与える影響**、**目的関数の違い**、**転用時の注意点**を整理する。

結論:
1. **代謝プロファイルは本質的に異なる**: CHO は高乳酸産生・グルタミン分解が顕著なハムスター由来 mAb 生産系。iPSC は highly glycolytic なヒト多能性細胞で、乳酸蓄積・浸透圧ピーク・凝集体サイズが成長制限因子となる。〔事実：Manstein 2021; Huang 2020〕
2. **凝集体サイズは独立した CPP**: iPSC 浮遊培養では凝集体径が酸素/栄養拡散、シアストレス、品質（未分化性）を同時に規定。CHO の単一懸濁とは異なる。〔事実：Borys 2021; Huang 2020〕
3. **目的関数は mAb タイトルから多能性マーカーへ**: CHO 最適化の KPI は抗体タイトル/糖鎖。iPSC では OCT4/SOX2/NANOG/SSEA/TRA 等の多能性マーカー、核型、生存率が主目的関数。〔事実：各種 QC ガイダンス〕
4. **CHO 数値を iPSC にそのまま転用しない**: 乳酸閾値、アンモニア閾値、浸透圧許容範囲、撹拌最適 rpm、灌流率は細胞株・培地・反応器形状で大きく変動。〔推定/未確定：Xing 2008; Mabion 2025〕
5. **A 層設計への含意**: L1 のレシピ DSL、L2 BO の目的関数・制約、L3 HMI の説明に「CHO vs iPSC 転換注意」を組み込む必要がある。〔設計提案〕

---

## 2. 調査背景と位置づけ

### 2.1 補完すべき相違点

`docs/design/alignment_with_downloaded_report.md` §4.8 では、レポートが CHO/mAb 中心であるのに対し auto_cell は iPSC 浮遊/凝集体灌流であり、**CPP 値・制御戦略・目的関数を iPSC に再解釈する必要**があると結論付けられた。

本調査が補完すべき観点:
- CHO と iPSC の代謝特性の違い（グルコース消費、乳酸生成、アンモニア、グルタミン）
- 凝集体形成が CPP に与える影響（撹拌、シア、酸素拡散）
- mAb タイトル vs 未分化/多能性品質マーカーの目的関数の違い
- CHO の最適化成果を iPSC に転用する際の注意点

### 2.2 A 層スコープ遵守

本調査は A 層（iPSC 浮遊/凝集体バイオリアクター制御）に限定する。樹立（reprog）、分化（diff）、双腕ロボ、接着培養、GMP 完全準拠は設計境界とする。

---

## 3. CHO と iPSC の代謝特性の相違

### 3.1 CHO 細胞の代謝プロファイル

CHO 細胞はハムスター卵巢由来の抗体生産宿主であり、以下の特徴を持つ。

| 特性 | CHO 典型値/傾向 | 出典 | 確度 |
|---|---|---|---|
| グルコース消費 | 高い；最低 2–3 g/L（約 11–17 mM）維持が推奨 | Mabion 2025 | 推定（業界ガイダンス） |
| 乳酸産生 | 急速な乳酸蓄積；タイトル低下・細胞死を誘導 | Mabion 2025; GFI 2025 | 事実 |
| 乳酸/グルコース比 | 親株で 0.79、代謝改変株で 0.17（batch/fed-batch） | Toussaint et al. 2016 | 事実 |
| アンモニア阻害 | 5.1 mM で成長阻害、8 mM で 50% 成長低下 | Mabion 2025; Xing 2008 | 事実（CHO 細胞） |
| グルタミン分解 | 活発；アンモニア主要源 | Cole 2017（PhD thesis） | 事実 |
| 浸透圧許容 | 最適 280–320 mOsm/kg、380–450 mOsm/kg 超で成長低下 | GFI 2025; Xing 2008 | 事実（CHO/哺乳類一般） |

〔事実〕CHO 親株では乳酸/グルコース比が 0.79 に達し、PYC2 発現株では 0.17 まで低下する。乳酸は pH 低下・浸透圧上昇を介してタイトル低下と細胞死を引き起こす。〔Toussaint et al. 2016, DOI 10.1016/j.jbiotec.2015.11.010〕

〔事実〕Xing et al. 2008 は CHO 培養で乳酸、アンモニア、浸透圧、 pCO₂ の阻害閾値を多変量解析により同定。アンモニア 5 mM で細胞密度が 10% 減少、10 mM で糖鎖パターンが変化。〔Xing et al. 2008, DOI 10.1021/bp070466m, PMID 18422365〕

### 3.2 iPSC の代謝プロファイル

iPSC は highly glycolytic な代謝を持つヒト多能性細胞であり、CHO とは異なる制約が成長を規定する。

| 特性 | iPSC 典型値/傾向 | 出典 | 確度 |
|---|---|---|---|
| グルコース消費 | 高密度で急増；飢餓は成長制限因子 | Manstein 2021 | 事実 |
| 乳酸蓄積 | 高グルコース供給に伴い大量乳酸分泌；pH 低下を誘導 | Manstein 2021; Zweigerdt interview | 事実 |
| 乳酸閾値 | Manstein モデルでは K_Lac=50 mM を阻害定数として採用 | Manstein 2021 Table 1 | 事実（モデル値） |
| グルタミン閾値 | K_Gln=0.01 mM（Manstein モデル） | Manstein 2021 Table 1 | 事実（モデル値） |
| 浸透圧 | 高密度培養でピーク；K_Osm=500 mOsm/kg（Manstein モデル） | Manstein 2021 Table 1 | 事実（モデル値） |
| 多能性維持 | 乳酸/アンモニア/浸透圧の変動が未分化性に影響 | Huang 2020; Seo 2021 | 推定 |

〔事実〕Manstein & Zweigerdt 2021 の hPSC 灌流撹拌槽プロセスでは、乳酸蓄積・浸透圧ピーク・グルコース飢餓を制御することで 7 日間で 35×10⁶ cells/mL（70 倍拡大）を達成。Table 1 の定数: µ=1.35/d, K_Glc=1.5 mM, K_Lac=50 mM, K_Gln=0.01 mM, K_Osm=500 mOsm/kg。〔Manstein et al. 2021, DOI 10.1002/sctm.20-0453, PMID 33660952〕

〔推定〕iPSC は未分化性を維持するために安定した微環境が必要。Terumo の Nathan Frank 氏は「glucose levels が低下しすぎず、lactate levels が急上昇しない一貫した微環境」が多能性維持に重要と述べている。〔RegMedNet interview 2025〕

### 3.3 代謝閾値の比較と転用注意

| パラメータ | CHO 文献値 | iPSC（Manstein） | 転用可否 | 確度 |
|---|---|---|---|---|
| 乳酸阻害 | 15–50 mM（株依存） | K_Lac=50 mM | **不可：株・培地依存** | 事実/推定 |
| アンモニア阻害 | 5 mM（10% 成長低下） | 未確定（監視のみ） | **不可：iPSC 固有値未確定** | 未確定 |
| 浸透圧 | 380–450 mOsm/kg 超で成長低下 | K_Osm=500 mOsm/kg | **不可：培地・密度依存** | 事実/推定 |
| グルコース下限 | 2–3 g/L（11–17 mM）推奨 | K_Glc=1.5 mM | **不可：iPSC は低濃度でも制限** | 事実（iPSC モデル値） |
| グルタミン | 高濃度補充が一般的 | K_Gln=0.01 mM | **不可：iPSC は低濃度制限** | 事実（iPSC モデル値） |

〔未確定〕アンモニアの iPSC ネイティブ閾値は現時点で確立されていない。auto_cell A 層では監視値（仮 4–6 mM）として扱い、実データで再校正が必要。〔`docs/design/ground_knowledge/integrated_report.md` §3.1〕

---

## 4. 凝集体形成が CPP に与える影響

### 4.1 凝集体サイズと酸素/栄養拡散

iPSC 浮遊培養では細胞が凝集体を形成する。凝集体径が大きくなると、中心部への酸素/栄養拡散が制限され壊死コアが形成される。

〔事実〕Huang et al. 2020 は、凝集体内の酸素拡散限界を血管からの距離 100–200 µm と参照し、収穫日の平均凝集体径を 300 µm 以下に制御する攪拌スキームを開発。〔Huang et al. 2020, Cell Gene Ther Insights〕

〔事実〕Borys et al. 2021 は Vertical-Wheel 撹拌槽で 40 rpm が最大増殖を示し、day 5 の凝集体径が 169–275 µm、**>400 µm で壊死が予想される**と報告。〔Borys et al. 2021, Stem Cell Res Ther 12:55, DOI 10.1186/s13287-020-02109-4, PMID 33436078〕

〔事実〕STEMCELL Technologies の hPSC 凝集体プロトコルでは、理想的な平均凝集体径を 50–200 µm とする。〔STEMCELL PIS 10000031886〕

〔推定〕神経オルガノイドのモデリングでは、直径 400 µm のエンブロイドボディで中心部酸素濃度が 200 µm のものより 50% 低下し、直径 650 µm 超で壊死が顕在化。〔arXiv 2023 stochastic model; biorxiv 2025 neural organoid model〕

### 4.2 攪拌とシアストレス

凝集体サイズ制御の主レバーは攪拌であるが、iPSC はシアに敏感。

〔事実〕Borys et al. 2021 は Vertical-Wheel で最適攪拌を 40–60 rpm と報告。auto_cell A 層の 50–120 rpm 上限は、安全マージンを含む設計選択。〔Borys 2021; `docs/design/kg_to_auto_cell.md` §4〕

〔事実〕Zweigerdt らは、hiPSC 高密度培養で「適切な攪拌速度で凝集体径を ~300 µm 以下に抑える」ことを成長制限因子として挙げている。〔Eppendorf eBook 2023; Zweigerdt interview〕

〔推定〕工程スケールアップ時、攪拌 rpm の幾何学的スケーリング（tip speed、P/V、混合時間）だけでなく、**凝集体径分布**と**局所シア率**を同時に考慮する必要がある。〔Huang 2020; Borys 2022 PhD thesis〕

### 4.3 凝集体サイズを CPP としての扱い

auto_cell A 層ではすでに `cpp_aggregate_diameter`（150–350 µm）が CPP として定義されている。本調査で追加される視点:
- 凝集体径は「品質代理指標」としても機能（大径→壊死→未分化性低下）
- 攪拌レバーと灌流レバーの相互作用（攪拌上昇→凝集体破砕だがシア増大）
- 継代トリガとしての凝集体径逸脱

〔設計提案〕L1 ルールエンジンで `aggregate_out_of_range` イベントを、径上限（350 µm）だけでなく「径分布の歪度（大凝集体割合）」も考慮すべき。〔未確定：画像解析の実装段階で検討〕

---

## 5. 目的関数の違い：mAb タイトル vs 多能性品質マーカー

### 5.1 CHO の目的関数

CHO fed-batch/perfusion の最適化目標は通常:
- 抗体タイトル（g/L）
- 収率（viable cell density × specific productivity）
- 糖鎖パターン（G0F/G1F/G2F 比率など CQA）
- 培地コスト/プロセス時間

〔事実〕Toussaint et al. 2016 は PYC2 発現 CHO で抗体タイトルが 28–35% 向上し、これは細胞密度上昇と培養長期化による。〔Toussaint et al. 2016〕

### 5.2 iPSC の目的関数

iPSC 浮遊拡大の目的関数は「細胞数最大化」だけでなく、以下の品質属性を含む。

| 品質属性 | マーカー/手法 | 出典 | 確度 |
|---|---|---|---|
| 多能性（核内） | OCT4, SOX2, NANOG | Amsbio QC guide; WhiteRose 2023 | 事実 |
| 多能性（細胞表面） | SSEA-3, SSEA-4, TRA-1-60, TRA-1-81 | Amsbio QC guide; AxolBio poster | 事実 |
| 同一性/遺伝子異常 | 核型、STR、同一性 | Ubrigene 2024 | 事実 |
| 自発分化 | 形態学、ラインage marker | `qccrit` node | 推定 |
| 生存率 | Trypan blue / フロー | Huang 2020 | 事実 |
| 凝集体形態 | 径、円形度、壊死コア | Borys 2021; Gilpin 2026 | 推定 |

〔事実〕Seo et al. 2021 の Vertical-Wheel DoE では、OCT4/SOX2 陽性率 >90% を維持しつつ凝集体融合を抑制する培地添加物を最適化。OCT4 と SOX2/NANOG は異なる添加物によって制御され、**単一目的関数では最適化困難**であることを示唆。〔Seo et al. 2021, bioreactor iPSC aggregate stability publication〕

〔推定〕BO 目的関数は「細胞収量 × 生存率 × 未分化マーカー陽性率 × 凝集体適正サイズ比率」の多目的または重み付きスカラーとなる。重みは細胞株・最終用途（分化先）で変動。〔ADR-0001; `integrated_report.md` §2.3〕

### 5.3 目的関数転換の設計含意

- CHO の「タイトル最大化」に向く低グルコース戦略は、iPSC では多能性維持と相反する可能性がある。
- CHO の「高比重培養→長期培養」は、iPSC では凝集体サイズ制限・遺伝子異常リスクから長期化しにくい。
- **L2 BO の目的関数は、iPSC 特異的な品質項を必ず含める**必要がある。〔設計提案〕

---

## 6. CHO → iPSC 転用時の注意点

### 6.1 数値転用禁止リスト

以下の CHO 由来数値を iPSC にそのまま転用しない。

| 項目 | CHO 値/傾向 | iPSC での扱い | 理由 |
|---|---|---|---|
| 乳酸閾値 | 15–50 mM（株依存） | K_Lac=50 mM は Manstein モデル値；実株で再校正 | 細胞種・培地・密度依存 |
| アンモニア閾値 | 5 mM で成長阻害 | **iPSC 固有値未確定**；監視のみ | 未確定 |
| 浸透圧上限 | 380–450 mOsm/kg | K_Osm=500 mOsm/kg（Manstein モデル値） | 培地・密度依存 |
| グルコース下限 | 2–3 g/L 維持 | K_Glc=1.5 mM | iPSC は低濃度制限 |
| 攪拌最適 rpm | 80–120 rpm（インペラ槽） | 40–60 rpm（Vertical-Wheel）、80 rpm（DASbox 150mL） | 反応器形状・凝集体制御 |
| 灌流率 | CHO perfusion 0.029–0.075 L/h（5L） | 0→7 vvd（Manstein） | スケール・プロセス依存 |
| 目的関数 | mAb タイトル | 収量×生存率×多能性マーカー | 製品が細胞そのもの |

### 6.2 制御戦略転用禁止リスト

- **CHO の低乳酸株育成戦略**（PYC2 等の代謝改変）→ iPSC では遺伝子改変が治療用製品として受け入れられない。
- **CHO の高比重・長期培養**→ iPSC では凝集体サイズ制限・多能性喪失・核型異常リスク。
- **CHO の antibody titer 特化 feed 設計**→ iPSC では成長因子・ROCK 阻害剤・凝集体安定化添加物が重要。
- **CHO の 2D/単一懸濁に基づく画像解析**→ iPSC 浮遊凝集体の形態解析に読み替えが必要。

### 6.3 転用可能な一般論

- **灌流による代謝物洗浄・栄養供給の概念**は両者で共通。
- **in-line センシング（Raman、capacitance）の価値**は共通（ただし iPSC 再校正必須）。
- **BO/DoE による多変数最適化の枠組み**は共通。
- **Human-on-the-loop + 決定的制御コア**の安全設計は共通。

---

## 7. A 層設計への具体的含意

### 7.1 L1 決定的レシピ/ルールエンジン

- トリガ閾値は `K_Glc=1.5 mM`, `K_Lac=50 mM`, `K_Osm=500 mOsm/kg`（Manstein モデル値）を初期値とし、実株データで再校正。
- アンモニアはイベント化せず監視ログに留め、閾値は研究者ヒアリングまたは実験決定。
- 凝集体径トリガは平均径だけでなく大径凝集体割合（>400 µm）も考慮。

### 7.2 L2 ベイズ最適化

- 目的関数に必ず多能性マーカー（OCT4/SOX2/NANOG/SSEA/TRA）陽性率を含める。
- Safe BO の制約に「凝集体径上限」と「シア推定値」を追加。
- CHO 由来の探索空間（グルコース濃度範囲等）を iPSC 用に再設定。

### 7.3 L3 LLM オーケストレータ/HMI

- 研究者への説明に「この提案は CHO 由来の知見ではなく、iPSC モデル/実データに基づく」旨を明示。
- 包絡線外提案時に、CHO 値との差異を簡潔に注記。

### 7.4 技術的統制/監査

- CPP 閾値の出典（Manstein 2021 / CHO 文献 / 未確定）をメタデータとして記録。
- 閾値変更は研究者承認＋ALCOA-lite ログ。

---

## 8. 未確定事項・次ステップ

| # | 項目 | 影響層 | 次ステップ |
|---|---|---|---|
| U1 | アンモニアの iPSC ネイティブ閾値 | L1 CPP | 文献サーチ or 実験決定 |
| U2 | 乳酸 50 mM 閾値の細胞株依存性 | L1/L2 | 実データでの再校正 |
| U3 | 凝集体径分布（歪度/大径割合）の品質相関 | L1/L2 | 画像解析データ取得 |
| U4 | BO 目的関数の重み（収量 vs 多能性 vs コスト） | L2 | 研究者ヒアリング |
| U5 | シアストレスの定量指標（Kolmogorov 長等） | L1/L2 | 流体解析・実証 |
| U6 | CHO 由来の高比重培養戦略の iPSC 適用可否 | 設計境界 | 基本不可、例外検討 |

---

## 9. 出典

| ID | タイトル | URL/DOI/PMID/PMCID | 確度 |
|---|---|---|---|
| Manstein 2021 | High density bioprocessing of human pluripotent stem cells by metabolic control and in silico modeling | DOI 10.1002/sctm.20-0453; PMID 33660952; PMC8235132 | 事実 |
| Manstein 2021 protocol | Process control and in silico modeling strategies for enabling high density culture of hPSCs in STBRs | STAR Protocols 2(4):100988; PMC8666714 | 事実 |
| Borys 2021 | Overcoming bioprocess bottlenecks in large-scale expansion of hiPSC aggregates in vertical-wheel bioreactors | DOI 10.1186/s13287-020-02109-4; PMID 33436078; PMC7805206 | 事実 |
| Huang 2020 | Process development and scale-up of pluripotent stem cell manufacturing | Cell Gene Ther Insights 2020 | 事実 |
| Xing 2008 | Identifying inhibitory threshold values of repressing metabolites in CHO cell culture | DOI 10.1021/bp070466m; PMID 18422365 | 事実（CHO） |
| Toussaint 2016 | Metabolic engineering of CHO cells to alter lactate metabolism | J Biotechnol 217:122-131; DOI 10.1016/j.jbiotec.2015.11.010 | 事実（CHO） |
| Mabion 2025 | Optimizing CHO Cell Cultures via Metabolite Analysis | https://www.mabion.eu/science-hub/articles/metabolite-nutrient-analysis-upstream-process-optimization/ | 推定（業界知見） |
| GFI 2025 | Technical Report: Optimizing CM Techno-economics | https://gfi.org/wp-content/uploads/2025/10/Technical-report-Optimizing-CM-Technoeconomics-2025.pdf | 推定（CHO/培養肉） |
| RegMedNet 2025 | Minimizing variability and maximizing quality in iPSC cultures (interview with Nathan Frank) | https://www.regmednet.com/.../nathan-frank_terumo/ | 推定 |
| Seo 2021 | Addressing bioreactor hiPSC aggregate stability using DoE | bioreactor_iPSC_aggregate_stability_publication.pdf | 事実/推定 |
| STEMCELL PIS | hPSC Aggregate Culture Product Information Sheet | 10000031886-PIS_01.pdf | 事実 |
| Amsbio QC | Quality Control of Stem Cells | https://www.amsbio.com/research-areas/stem-cell/stem-cells-quality-control | 事実 |
| AxolBio poster | Utilizing flow cytometry within a QC process for iPSC manufacturing | https://axolbio.com/publications/poster-utilizing-flow-cytometry-within-a-quality-control-process-for-an-ipsc-based-manufacturing-facility/ | 事実 |
| Ubrigene 2024 | QC for iPSC-derived therapy | https://www.ubrigene.com/qc-for-ipsc-derived-therapy/ | 推定 |
| WhiteRose 2023 | A short history of pluripotent stem cells markers | DOI 10.1016/j.stemcr.2023.08.002 | 事実 |
| Eppendorf eBook 2023 | Optimizing Cell and Gene Therapy Workflows | https://www.regmednet.com/wp-content/uploads/2023/11/Eppendorf_Cell-and-Gene-Therapy-Workflows_eBook_compressed.pdf | 事実 |
| Chen 2014 | Human pluripotent stem cell culture: considerations for maintenance, expansion, and therapeutics | Cell Stem Cell 14:13-26 | 事実 |
| Borys 2022 PhD | Scale-up of mESC aggregates in stirred suspension bioreactors | University of Calgary thesis | 推定 |

---

*本レポートは auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御）に限定。CHO 由来の数値を iPSC にそのまま転用しないことを原則とし、すべての主張に出典と確度を付与した。*
