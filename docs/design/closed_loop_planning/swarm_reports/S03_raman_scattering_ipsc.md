# S03: iPSC 浮遊凝集体培養における in-line Raman 光散乱補正と校正戦略

> **担当**: PAT / Raman 調査エージェント（Agent Swarm S03）  
> **Scope**: auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御、Manstein 型灌流 0→7 vvd、目標密度 ~35×10⁶ cells/mL）  
> **作成日**: 2026-06-30  
> **前提**: ADR-0001（L0 局所 PID + L1 決定的レシピ/ルール + L2 ベイズ最適化 + L3 薄い LLM オーキストレータ）、Human-on-the-loop、R&D 一次

---

## 1. Executive Summary

1. **iPSC 浮遊凝集体バイオリアクターへの in-line Raman 実証は限定的**〔事実：Costa 2024; Polanco 2020〕。CHO/mAb では TRL 8–9 だが、iPSC 凝集体マトリックス（mTeSR/E8 系培地、凝集体 150–350 µm、高密度 ~3.5×10⁷ cells/mL）への適用は未確定。〔推定〕
2. **iPSC 特異的な再校正が必須**〔推定〕。培地組成、代謝物濃度範囲、凝集体サイズ、細胞密度、シア感受性が CHO と大きく異なる（Manstein 2021; Borys 2021）。CHO の chemometric モデルをそのまま転用することは技術的に不合理。〔推定〕
3. **光散乱補正は RMSEP 改善のカギ**〔事実：Yang 2024; Iversen 2014〕。凝集体・高密度細胞懸濁液による Mie 散乱で Raman 強度が減衰し、Beer-Lambert 則では記述できない非線形な関係を示す。
4. **cell-scattering correction の定式化例が存在する**〔事実：Yang 2024〕。`Log(R_cell) = a × C^b`（`R_cell = I_cell / I_0`、C は細胞濃度）を用いて、水ピーク（~1645 cm⁻¹）積分から細胞濃度を推定し、対象バンドを補正する方法が酵母発酵で実証された。iPSC 凝集体へのパラメータ転移は未確定。〔未確定〕
5. **PLS モデル構築のバッチ数目安**〔事実/推定〕：初期実証 3–5 バッチ、実用的ロバストモデル 5–15 バッチ、スケール/株間転移には 10 バッチ以上。Nova FLEX2 を正解ラベル、capacitance を VCD アンカーとする。〔推定〕
6. **capacitance VCD・凝集体径を共変量に加える設計は有効と推定**〔推定〕。文献的裏付けは CHO/酵母だが、光散乱補正と組み合わせることで iPSC 高密度下の精度向上が期待される。
7. **内部標準（水ピーク 1600–1700 cm⁻¹）による補正**〔事実：Yang 2024; Iversen 2014〕。培地中の水濃度はほぼ一定なので、水バンド減衰を基準にスペクトル強度を正規化できる。
8. **前処理は SNV/MSC/EMSC + Savitzky-Golay 微分が標準**〔事実：Pavurala 2025; Saeys; Borg 2025〕。データセットによって最適な組み合わせは変わるため、候補を比較評価する。
9. **v1 → v1.5 → v2 の移行は、バッチ数・精度基準・信頼度スコアで段階化する**〔設計判断〕。v1 は観測/記録のみ、v1.5 はアドバイザリ、v2 は `validate_tool_call` 包絡線内での閉ループ入力候補。

---

## 2. iPSC Raman 適用事例

### 2.1 哺乳類細胞培養一般（参照：CHO/mAb/HEK293/T-cell）

| 研究 | 対象 | 計測対象 | 主な成果 | 出典 |
|---|---|---|---|---|
| Abu-Absi et al. 2011 | CHO fed-batch（3 L/15 L/500 L） | glucose, lactate, glutamine, glutamate, ammonium, VCD, TCD, osmolality | in-line Raman による複数パラメータ同時予測の産業実証 | DOI 10.1002/bit.23023 |
| Whelan et al. 2012 | CHO fed-batch（3 L/15 L） | glucose, glutamine, lactate, ammonia, glutamate, TCD, VCD | 3 L→15 L スケール転移成功（VCD を除く） | DOI 10.1002/btpr.1572 |
| Matthews et al. 2016 | CHO fed-batch | glucose, lactate | Raman ベース乳酸閉ループ制御。RMSEP glucose 0.27 g/L、lactate 0.20 g/L | DOI 10.1002/bit.26018 |
| Berry et al. 2015 | CHO | growth, metabolites | 200 L/2000 L スケール横断予測 | DOI 10.1002/btpr.2035 |
| Santos et al. 2018 | CHO mAb | metabolites, titer | 産業利用に向けた信頼性評価 | DOI 10.1002/btpr.2635 |
| Müller et al. 2024 | CHO | multiple | Indirect Hard Modeling (IHM) によるロバストモデル | DOI 10.1002/bit.28724 |
| Graf et al. 2022 | CHO 灌流 | glucose | Raman による灌流培養非侵襲連続制御 | DOI 10.3389/fbioe.2022.719614 |
| Baradez et al. 2018 | ドナー由来 T-cell（細胞治療） | glucose, lactate, glutamine, ammonia, cell concentration, viability | 攪拌槽バイオリアクターで in-line Raman + PLS/単変量モデル | DOI 10.3389/fmed.2018.00047 |

**解釈**: これらは **CHO/mAb/T-cell 由来**の実績であり、iPSC 浮遊凝集体への直接的適用を保証しない〔事実/推定〕。

### 2.2 iPSC/hPSC への適用

| 研究/レビュー | 対象 | 主張 | 出典 |
|---|---|---|---|
| Costa et al. 2024 | cell therapy bioprocessing（包括レビュー） | Raman は細胞密度、生存率、代謝物、細胞同一性バイオマーカーの同時計測に潜在力。ただし iPSC 浮遊凝集体への in-line 実装例は限定 | DOI 10.1016/j.biotechadv.2024.108166 |
| Polanco et al. 2020 | iPSC 品質維持技術 | Raman/NIR は代謝物モニタリングの有望な online probe。凝集体形成の再現性と多能性維持がスケーラビリティの鍵 | DOI 10.1016/j.tibtech.2020.04.006 |
| Hsu et al. 2020 | hiPSC → neural 分化（single-cell Raman） | グリコーゲンを Raman biomarker に iPSC と神経細胞を 97.5% 精度で分類 | DOI 10.1073/pnas.2001906117 |
| Baradez et al. 2018 | T-cell 免疫細胞治療 | 細胞治療バイオリアクターでの in-line Raman 監視実証 | DOI 10.3389/fmed.2018.00047 |
| Isidro et al. 2021 | hiPSC 拡大・肝分化（3D） | **capacitance** による online monitoring。Raman は直接使用せず | DOI 10.1002/bit.27751 |
| Manstein et al. 2021 | hPSC 灌流撹拌槽 | in-line Raman は使用せず、at-line/off-line 解析で代謝物を追跡 | DOI 10.1002/sctm.20-0453 |

**解釈**: iPSC/hPSC の**浮遊凝集体培養そのもの**に in-line Raman を適用した実証研究は、公開文献では**稀または未確定**である〔推定/未確定〕。したがって、CHO/mAb 由来の TRL 8–9 評価を iPSC にそのまま転用できない。

### 2.3 ベンダー事例

| ベンダー/技術 | 主張 | 出典 |
|---|---|---|
| Sigma-Millipore / Bio4C PAT Raman（AN9376） | N-1 perfusion CHO で 5 バッチから glucose/lactate/VCD/TCD 等の PLS モデルを構築 | URL: sigmaaldrich AN9376 |
| MilliporeSigma One-Batch Calibration（AN13446） | 1 バッチ + 統計手法で glucose/lactate/VCD/titer のモデルを構築、3–6 バッチ標準法と同等以上 | URL: sigmaaldrich AN13446 |
| Thermo MarqMetrix AIO Raman（APN-0130） | 5 細胞株（CHO 系/HEK293）・5 培地・複数スケールで chemometric transferability を実証 | URL: thermofisher APN-0130 |
| Yokogawa Electric + 関西学院大学 | 培地データからの Raman 校正モデル。glucose RMSEP 0.23 g/L、lactate 0.29 g/L | Spectroscopy Online 2026-05-20 |
| Repligen MAVERICK | de novo モデルによる glucose/lactate/biomass 計測 | Repligen DOC043_1.PDF |
| Metrohm 2060 Raman | cell culture bioreactor の glucose/lactate in-line 計測。SEP glucose 0.20 g/L、lactate 0.12 g/L | Metrohm AN-PAN-1065 |

**解釈**: ベンダー事例も CHO/HEK293/発酵が中心。iPSC 凝集体マトリックスに対する検証は謳われていない〔推定〕。

---

## 3. 光散乱メカニズムと補正手法

### 3.1 光散乱のメカニズム

- Raman プローブは懸濁細胞/凝集体による **Mie 散乱**を受け、**Raman 強度が減衰**する〔事実：Yang 2024; Esmonde-White 2017〕。
- 散乱の影響は Beer-Lambert 則では記述できず、細胞濃度と非線形な関係を示す〔事実：Yang 2024〕。
- 凝集体径 150–350 µm は可視・近赤外レーザー波長（785 nm）と比較して大きく、複雑な散乱パターンを生じる〔推定：Yang 2024; Mie theory〕。
- 細胞密度の増加に伴い、水ピーク強度も減衰するが、水濃度は培地中でほぼ一定なので内部標準として利用可能〔事実：Yang 2024〕。

### 3.2 補正手法比較

| 手法 | 対象となる変動 | 利点 | 欠点 | 推奨用途 | 出典 |
|---|---|---|---|---|---|
| **SNV** | スペクトル全体の平均・分散（乗法的・加法的効果） | 計算が簡単、1 スペクトルずつ独立 | 化学情報も正規化、外れ値に弱い | ベースライン・強度差の粗補正 | Pavurala 2025; Saeys |
| **MSC** | 平均スペクトルに対する回帰（加法的・乗法的） | 物理的散乱モデルに近い | 参照スペクトル依存、外れ値に弱い | SNV と併せて比較評価 | Saeys; Borg 2025 |
| **EMSC** | MSC + 多項式ベースライン・波数依存項 | ベースラインと正規化を同時に処理、物理・化学効果の分離可能 | パラメータ調整が必要、計算コストやや高い | 異実験間バッチ差が大きい場合 | Saeys; Borg 2025; Pavurala 2025 |
| **Savitzky-Golay 微分** | ベースライン・緩やかな背景 | 加法的・乗法的効果を除去しやすい | ノイズ増幅、微分窓選択が重要 | 代謝物ピーク強調（1st/2nd derivative） | Pavurala 2025; Dong 2024 |
| **水ピーク内部標準** | プローブ・散乱による強度変動 | 培地中で水濃度が一定、簡便 | 硫酸ピーク等の他成分変動に影響される可能性 | cell-scattering correction の前段 | Yang 2024; Iversen 2014 |
| **cell-scattering correction** | 細胞密度に依存した非線形減衰 | Mie 散乱を明示的に補正 | バンドごとに係数推定が必要、iPSC パラメータは未確定 | 高密度・凝集体培養 | Yang 2024 |
| **VCD/凝集体径共変量** | 密度・サイズに依存した散乱 | PLS が密度変動を学習可能 | 共変量自体の誤差が伝播 | 高密度 iPSC 培養の補助 | 推定（Metze 2019; Rittershaus 2022 参考） |
| **EPO（External Parameter Orthogonalization）** | 外部要因（給餌・温度等） | ノイズ要因を直交除去 | 外部パラメータの正確な取得が必要 | 給餌イベント等の補正 | Anderson 2022 |

---

## 4. Cell-Scattering Correction の定量式

### 4.1 Yang et al. 2024 の定式化

酵母発酵（*Saccharomyces cerevisiae*）の in-line Raman で提案された非線形補正式：

```
Log(R_cell) = Log(I_cell / I_cell=0) = a × C^b
```

- `R_cell`: 減衰比（細胞あり/細胞なしの同じ混合物の強度比）
- `I_cell`: 細胞を含む懸濁液の Raman 強度
- `I_0`: 細胞を含まない標準溶液の Raman 強度
- `C`: 細胞濃度（例：g/L）
- `a`, `b`: バンドごとに決定されるフィッティング係数

**Yang 2024 の実測係数例（酵母、選択バンド）**:

| バンド (cm⁻¹) | a | b |
|---|---|---|
| 864–893 | -0.419 | 0.517 |
| 1037–1136 | -0.433 | 0.501 |
| 1272–1278 | -0.479 | 0.372 |
| 1437–1474 | -0.404 | 0.470 |

この指数関数は、細胞濃度が高くなると減衰が漸近する挙動を表現し、Iversen et al. 2014 の二次式より過学習リスクが低いと主張されている〔事実：Yang 2024〕。

**iPSC 凝集体への妥当性**: 式の形は Mie 散乱の非線形性を記述する上で妥当〔推定〕。ただし、`a`・`b` の値は細胞サイズ分布・凝集体径・培地屈折率によって変わるため、iPSC では実験的再推定が必要〔未確定〕。

### 4.2 水ピークを用いた細胞濃度推定

水バンド（1521–1800 cm⁻¹、中心 ~1645 cm⁻¹）の積分強度を内部標準として利用し、細胞濃度 `C` を推定する：

```
Ratio(C)_i = Σ_{c=i}^{c+i} I_cell(C) / Σ_{c=i}^{c+i} I_0
```

- `c`: 中心ピーク（1645 cm⁻¹）
- `i`: 積分幅（例：21 cm⁻¹ → 1624–1666 cm⁻¹）

最適幅は検証バッチでチューニングする。Yang 2024 の酵母例では `a_21 = -0.374`、`b_21 = 0.521`、RMSEP yeast = 0.4 g/L となった〔事実〕。

### 4.3 補正フロー

```text
1. ベースライン補正（ALS/多項式）
2. 水バンド（1521–1800 cm⁻¹）で細胞濃度 C を推定
3. 各対象バンド j で I_corrected,j = I_obs,j / exp(a_j × C^b_j)
4. PLS モデルへ入力
```

---

## 5. PLS モデル構築に必要なバッチ数・校正設計

### 5.1 バッチ数目安

| 目的 | 推奨バッチ数 | 根拠 |
|---|---|---|
| 初期実証 | 3–5 バッチ | 推定；操作範囲内の濃度変動をカバー |
| ロバストモデル | 5–15 バッチ | 事実/推定：bioprocesstools.com; Sigma AN9376（5 バッチ）; Dong 2024（15 バッチ） |
| スケール/クローン間転移 | 10 バッチ以上 | 推定：Yan 2024; Rowland-Jones 2021; Metze 2019 |
| 最低限の 1 バッチ校正 | 1 バッチ + 統計拡張 | 事実：MilliporeSigma AN13446（one-batch calibration）; Klaverdijk 2025（single compound augmentation） |

### 5.2 校正設計の要点

- **正解ラベル**: Nova BioProfile FLEX2（glucose/lactate/glutamine/osmolality/viability/細胞径）を主正解とする〔事実：Baradez 2018; Dong 2024〕。
- **サンプリング頻度**: 4–8 h 間隔、目標 100 サンプル以上〔推定：bioprocesstools.com; Yang 2024〕。
- **濃度範囲**: プロセス動態全体をカバー。glucose 0.1–7.7 g/L、lactate 0–4.5 g/L、glutamine 0–4 mM 等を目安〔推定：Manstein 2021; iPSC 培地設計〕。
- **交差検証**: leave-one-batch-out（LOB）が標準〔事実：Metze 2019; bioprocesstools.com〕。
- **外部検証**: 独立 2–3 バッチで RMSEP、R²、bias を評価〔推定〕。
- **LV 数**: 代謝物 3–8 LV、VCD 5–12 LV。過学習を避け RMSECV 最小点で選択〔事実：bioprocesstools.com〕。

### 5.3 性能目標（ICH Q2 基準を参考）

| 対象 | 目標 RMSEP | 目標 R² | 備考 |
|---|---|---|---|
| Glucose | ≤ 操作範囲の 10%（例 ≤0.3–0.5 g/L） | ≥ 0.95 | CHO 実績 0.2–0.5 g/L〔事実〕 |
| Lactate | ≤ 操作範囲の 10%（例 ≤0.2–0.3 g/L） | ≥ 0.95 | CHO 実績 0.1–0.3 g/L〔事実〕 |
| Glutamine | ≤ 操作範囲の 10%（例 ≤0.2 mM） | ≥ 0.92 | 弱ピークのため注意〔事実〕 |
| VCD | 相対誤差 ±15–20% | 0.85–0.93 | Raman は間接的；capacitance をアンカーに〔事実：bioprocesstools.com〕 |

---

## 6. Capacitance VCD を共変量とする PLS モデル

### 6.1 なぜ capacitance を組み合わせるか

- Raman による VCD 予測は間接的で精度が低く（R² 0.85–0.93）、細胞株・培地間で転移しにくい〔事実：bioprocesstools.com; Berry 2015〕。
- Capacitance（誘電分光）は、細胞膜の分極を利用し、生細胞体積に比例する信号を得られる〔事実：Metze 2019; Rittershaus 2022〕。
- Manstein 2021 の hPSC 灌流撹拌槽でも capacitance と offline VCD が定性的一致した経験がある〔事実：kg_to_auto_cell.md §4.2〕。

### 6.2 共変量の入れ方（設計提案）

PLS の X ブロックを以下で拡張する：

```
X = [preprocessed_spectra, log(VCD_cap + 1), aggregate_diameter_um, viability_if_available]
```

- `VCD_cap`: in-line capacitance から推定した VCD（または生 capacitance）
- `aggregate_diameter_um`: at-line 画像由来の平均凝集体径
- 凝集体径分布の歪度・大径割合（>400 µm）も追加可能〔推定〕

**効果**: 散乱強度の変動を「細胞密度・凝集体サイズ」という物理量で説明し、PLS が化学情報に集中しやすくなると期待される〔推定〕。

**注意**: capacitance も細胞株・培地ごとに再校正が必要〔事実：Metze 2019〕。また、死細胞や細胞径変化の影響を受ける〔事実：Rittershaus 2022〕。

---

## 7. 内部標準（水ピーク 1600–1700 cm⁻¹）による補正

### 7.1 実装方法

1. **水バンドの積分**: 各スペクトルで `1521–1800 cm⁻¹`（または `1600–1700 cm⁻¹`）の領域を積分する。
2. **基準スペクトル**: 細胞を含まない培地（day 0 または spiked standard）の同領域積分値を `I_water_0` とする。
3. **正規化係数**: `scale = I_water_0 / I_water_t`
4. **スペクトル補正**: `I_corrected = I_raw × scale`（または各対象ピークに適用）

Yang 2024 では、単純な水ピーク強度ではなく、**積分幅を変えながら cell concentration 推定の RMSEP を最小化する幅**を選定した（1624–1666 cm⁻¹）〔事実〕。

### 7.2 注意点

- 培地組成（特に硫酸イオン・グルタミン等）が変わると水ピーク形状に影響する可能性がある〔推定〕。
- 硫酸ピークを内部標準とする方法もあるが、給餌ボーラスで希釈される場合は補正が狂うリスクがある〔事実：Klaverdijk 2025〕。
- 水ピーク補正だけでは Mie 散乱の全影響を除去できないため、§4 の cell-scattering correction と組み合わせる〔推定〕。

---

## 8. SNV / MSC / EMSC の比較

| 項目 | SNV | MSC | EMSC |
|---|---|---|---|
| **定義** | 各スペクトルを平均 0・標準偏差 1 に標準化 | 平均スペクトルに対する線形回帰で加法的・乗法的項を除去 | MSC を拡張し、多項式ベースライン・波数依存項を含むモデルで補正 |
| **数式（概要）** | `x'_i = (x_i − x̄) / σ` | `x_i ≈ a_i + b_i × x_ref` → `x'_i = (x_i − a_i) / b_i` | `x_i = a_i + b_i × x_ref + Σ c_k × w_k + e` |
| **強み** | 簡便、1 スペクトル独立 | 物理的な散乱モデルに近い | ベースラインと正規化を同時に、実験条件差にも頑健 |
| **弱み** | 化学情報も正規化、外れ値影響 | 参照スペクトル依存、外れ値影響 | パラメータ調整・計算コスト |
| **使いどころ** | 最初のベンチマーク | SNV と比較して選択 | バッチ間・プローブ間差が大きい場合 |
| **実装難易度** | 容易 | 容易 | 中（多項式次数・重み選択） |
| **出典** | Barnes et al. 1989; Saeys | Geladi et al. 1985; Saeys | Martens & Stark 1991; Saeys; Borg 2025 |

実際には **SNV/MSC + Savitzky-Golay 微分 + ベースライン補正** を複数候補とし、leave-one-batch-out RMSECV で最適を選択する〔推定〕。

---

## 9. CHO → iPSC モデル転移可能性と転移学習戦略

### 9.1 転移の制約要因

| 要因 | CHO | iPSC 浮遊凝集体 | 転移への影響 |
|---|---|---|---|
| 培地 | CD-CHO/ExpiCHO 等 | mTeSR/E8/StemFit 等 | マトリックススペクトルが異なる〔推定〕 |
| 代謝プロファイル | 抗体産生、乳酸蓄積傾向 | 未分化維持、乳酸再利用、高グルタミン依存 | ピーク強度・相関構造が異なる〔推定〕 |
| 細胞サイズ/凝集体 | 単一懸濁（~10–20 µm） | 凝集体 150–350 µm | 光散乱・遮蔽効果が大きい〔推定〕 |
| 細胞密度 | 通常 1–3×10⁷ cells/mL | ~3.5×10⁷ cells/mL | 高密度による非線形減衰〔推定〕 |
| 品質指標 | mAb タイトル | 未分化マーカー、多能性 | Raman からの代理推定は未確定〔未確定〕 |

### 9.2 転移学習戦略（設計提案）

| 戦略 | 内容 | 期待効果 | 出典 |
|---|---|---|---|
| **iPSC 特異再校正** | CHO モデルを完全に捨て、iPSC run データで 5–15 バッチ再構築 | 最も信頼性高い | 本調査の推奨 |
| **Standards-based model + cell-scattering correction** | 純粋培地中の標準スペクトルで PLS を構築し、Mie 散乱補正で適用 | バッチ依存を減らし、転移コストを下げる可能性 | Yang 2024; Klaverdijk 2025 |
| **Single-compound augmentation** | 1 バッチのプロセススペクトルに、glucose/lactate/glutamine の単独ピーク情報を合成的に加える | 少ない run で design space を広げる | Klaverdijk 2025 |
| **Piecewise Direct Standardization (PDS)** | CHO ソースと iPSC ターゲットのスペクトル対応を局所的に学習 | 一部転移可能な場合に有効 | Pétillot 2020 |
| **Domain Adaptation / Transfer PLS** | ソース（CHO）とターゲット（iPSC）の分布差を最小化する潜在変数を学習 | データが少ないターゲットで有効かもしれない | Machleidt 2024; Rowland-Jones 2021 |
| **Online updating / JITL** | 新しい iPSC バッチデータを逐次追加・忘却 | ドリフトに対応 | 推定 |

**結論**: CHO → iPSC の直接転移は推奨しない。初期は iPSC 特異データで再構築し、将来データが蓄積したら転移学習で効率化を検討する〔設計判断〕。

---

## 10. 精度目標（RMSEP/R²）と到達条件

### 10.1 A 層 iPSC 向け暫定目標

| 変数 | 操作範囲（iPSC 仮定） | 目標 RMSEP | 目標 R² | 備考 |
|---|---|---|---|---|
| Glucose | 0.1–7.7 g/L | ≤ 0.3 g/L（範囲の 4% 以下） | ≥ 0.96 | v2 閉ループに必要〔推定〕 |
| Lactate | 0–4.5 g/L | ≤ 0.2 g/L（範囲の 4% 以下） | ≥ 0.96 | 同上〔推定〕 |
| Glutamine | 0–4 mM | ≤ 0.2 mM | ≥ 0.92 | 弱ピーク〔推定〕 |
| VCD | 0–40×10⁶/mL | 相対誤差 ≤ 15% | ≥ 0.90 | capacitance を併用〔推定〕 |
| Osmolality | 250–500 mOsm/kg | ≤ 10 mOsm/kg | ≥ 0.90 | 複合ピーク〔推定〕 |

**到達条件**:
- 5 バッチ以上の iPSC 校正データ（Nova FLEX2 正解）〔推定〕
- leave-one-batch-out Q² ≥ 0.85、外部検証 R² ≥ 0.90〔推定〕
- cell-scattering correction 適用後、RMSEP が補正前より 20% 以上改善〔推定〕
- 低信頼度（Q 残差/Hotelling T²）時の HITL エスカレーション動作確認〔設計判断〕

---

## 11. v1 / v1.5 / v2 移行条件の具体化

| 段階 | Raman の位置づけ | 必要な条件 | Human-on-the-loop |
|---|---|---|---|
| **v1（Phase 1）** | **観測・記録のみ**。Nova FLEX2 を正解ラベルとしてデータ蓄積。Raman 推定値は HMI 表示に使わない。 | - Raman プローブ設置・滅菌確認  <br>- Nova FLEX2 校正済  <br>- 3 バッチ以上の時系列スペクトル取得 | 不要（記録のみ） |
| **v1.5（Phase 1 後期）** | **アドバイザリ入力**。glucose/lactate/glutamine 推定値を L1 イベントの参考情報として提示。制御アクションは人承認。 | - 5 バッチ以上の iPSC 校正  <br>- LOB Q² ≥ 0.85、外部検証 R² ≥ 0.90  <br>- 水ピーク内部標準・SNV/MSC 前処理確立  <br>- 信頼度スコア（Q 残差/T²）実装 | 必須：低信頼度・外挿時は Nova 優先 |
| **v2（Phase 2）** | **閉ループ入力候補**。`validate_tool_call` の包絡線内で灌流/給餌トリガに使用。 | - 10 バッチ以上の iPSC 校正  <br>- cell-scattering correction 適用・パラメータ確定  <br>- 外部検証 RMSEP ≤ 操作範囲の 10%、R² ≥ 0.95（glucose/lactate）  <br>- ドリフト監視・再校正トリガ確立  <br>- Annex 22-ready 技術的統制（モデルカード・バージョン固定・静的決定論的証明） | 必須：包絡線外・外挿・再校正時 |

---

## 12. 実装方針（Python）

### 12.1 推奨ライブラリ

| 用途 | ライブラリ | 備考 |
|---|---|---|
| スペクトル前処理 | `numpy`, `pandas`, `scipy.signal.savgol_filter` | SG 微分・平滑化 |
| ベースライン補正 | 自前 ALS（`scipy.sparse`）または `pybaselines` | 蛍光背景除去 |
| 散乱補正 | 自前 SNV/MSC/EMSC 関数 | 本レポート掲載 |
| PLS 回帰 | `sklearn.cross_decomposition.PLSRegression` | 標準的な NIPALS 実装 |
| 高度な化学量計学 | `pyPLS` / `pyspectra`（必要に応じて） | VIP、Q 残差、T² |
| 可視化 | `matplotlib`, `seaborn` | スペクトル・予測プロット |
| 監査・バージョン管理 | `pydantic`, `git`, `event_store` | ALCOA-lite |

### 12.2 校正パイプライン（Mermaid）

```mermaid
flowchart TD
    A[Raman raw spectra<br/>785 nm, 200-3200 cm-1] --> B{Quality gate<br/>saturation/cosmic ray}
    B --> C[Baseline correction<br/>ALS / polynomial]
    C --> D{Internal standard<br/>water peak 1521-1800}
    D --> E[Cell-scattering correction<br/>Log(R)=a*C^b]
    E --> F[SNV / MSC / EMSC]
    F --> G[Savitzky-Golay derivative]
    G --> H[Variable selection<br/>glucose 400-550/1000-1200 etc]
    H --> I[Augment VCD_cap & aggregate_diameter]
    I --> J[PLS Regression<br/>leave-one-batch-out CV]
    J --> K{Model acceptance?<br/>R2, RMSEP, Q-residual, T2}
    K -->|Yes| L[Deploy model version<br/>v1.5 advisory / v2 loop]
    K -->|No| M[Investigate outliers<br/>add batches / refine preprocessing]
```

### 12.3 Python コード例

#### SNV

```python
import numpy as np

def snv(spectra: np.ndarray) -> np.ndarray:
    """Row-wise Standard Normal Variate."""
    return (spectra - spectra.mean(axis=1, keepdims=True)) / spectra.std(axis=1, keepdims=True)
```

#### MSC

```python
def msc(spectra: np.ndarray, reference: np.ndarray | None = None) -> np.ndarray:
    """Multiplicative Scatter Correction."""
    if reference is None:
        reference = spectra.mean(axis=0)
    ref_mean = reference.mean()
    corrected = np.zeros_like(spectra)
    for i in range(spectra.shape[0]):
        slope, intercept = np.polyfit(reference, spectra[i], 1)
        corrected[i] = (spectra[i] - intercept) / slope * ref_mean
    return corrected
```

#### Cell-scattering correction

```python
def estimate_cell_concentration(
    spectra: np.ndarray,
    wavenumbers: np.ndarray,
    water_ref: float,
    band: tuple[float, float] = (1624, 1666),
) -> np.ndarray:
    """水バンド積分から細胞濃度指数を推定（仮）。"""
    mask = (wavenumbers >= band[0]) & (wavenumbers <= band[1])
    water_intensity = spectra[:, mask].sum(axis=1)
    ratio = water_intensity / water_ref
    return ratio  # 実際には ratio -> C への回帰を別途校正

def cell_scattering_correction(
    spectra: np.ndarray,
    concentration: np.ndarray,
    band_coeffs: dict[tuple[float, float], tuple[float, float]],
    wavenumbers: np.ndarray,
) -> np.ndarray:
    """
    Log(R_cell) = a * C^b を用いて各バンドを補正。
    band_coeffs: {(wmin, wmax): (a, b), ...}
    """
    corrected = spectra.copy()
    for (wmin, wmax), (a, b) in band_coeffs.items():
        mask = (wavenumbers >= wmin) & (wavenumbers <= wmax)
        attenuation = np.exp(a * (concentration ** b))  # R_cell
        corrected[:, mask] = spectra[:, mask] / attenuation[:, None]
    return corrected
```

#### PLS + 共変量 + 信頼度

```python
from sklearn.cross_decomposition import PLSRegression
from sklearn.model_selection import cross_val_predict
from sklearn.metrics import r2_score, mean_squared_error
import numpy as np

class RamanMetaboliteModel:
    def __init__(self, n_components: int = 5):
        self.pls = PLSRegression(n_components=n_components, scale=True)

    def fit(self, X_spec, covariates, y):
        """
        X_spec: 前処理済みスペクトル (n_samples, n_wavenumbers)
        covariates: (n_samples, n_cov) 例: log(VCD_cap+1), aggregate_diameter
        y: 正解濃度
        """
        X = np.hstack([X_spec, covariates])
        self.pls.fit(X, y)
        self.X_mean_ = X.mean(axis=0)
        self.X_std_ = X.std(axis=0)
        return self

    def predict(self, X_spec, covariates):
        X = np.hstack([X_spec, covariates])
        return self.pls.predict(X).ravel()

    def confidence(self, X_spec, covariates):
        """Hotelling T^2 と Q 残差を返す（簡易版）。"""
        X = np.hstack([X_spec, covariates])
        scores = self.pls.x_scores_
        loadings = self.pls.x_loadings_
        X_reconstructed = scores @ loadings.T
        q_residual = np.sum((X - X_reconstructed) ** 2, axis=1)
        t2 = np.sum((scores / scores.std(axis=0)) ** 2, axis=1)
        return {"q_residual": q_residual, "hotelling_t2": t2}
```

### 12.4 校正フロー図（テキスト）

```text
Run iPSC perfusion batch
        │
        ▼
Collect Raman spectra (every 1 min)
        │
        ▼
Sample → Nova FLEX2 + capacitance + aggregate image
        │
        ▼
Time-align reference values with spectra
        │
        ▼
Preprocess: baseline → water internal standard → SNV/MSC/EMSC → SG derivative
        │
        ▼
Cell-scattering correction (estimate C from water band, apply a,b per band)
        │
        ▼
Variable selection (glucose/lactate/glutamine bands) + VCD_cap + aggregate_size
        │
        ▼
PLS calibration (leave-one-batch-out CV)
        │
        ▼
Evaluate RMSEP, R², Q², bias, Q-residual, Hotelling T²
        │
        ▼
If acceptance criteria met → register model version → v1.5 advisory or v2 loop
```

---

## 13. 未確定事項と実験計画

| # | 項目 | 状態 | 次のアクション |
|---|---|---|---|
| U1 | iPSC 浮遊凝集体における Raman 実証データ | 未確定 | 協業パートナー/ベンダーでの PoC（3–5 バッチ） |
| U2 | 凝集体径・密度による光散乱補正の定量式 | 推定 | 標準添加/混合標準実験で a, b パラメータ推定 |
| U3 | Nova FLEX2 vs Raman の時間同期・遅延補正 | 未確定 | サンプリング/測定パイプライン設計 |
| U4 | 培地ロット間・細胞株間のモデル頑健性 | 未確定 | 複数ロット/株での検証バッチ |
| U5 | Raman 推定値の GAMP5/CSV 検証戦略 | 推定 | R&D 一次から GMP-ready への橋渡し文書化 |
| U6 | capacitance VCD を共変量とした場合の精度向上度 | 推定 | A/B テスト（with/without VCD covariate） |
| U7 | SNV vs MSC vs EMSC の iPSC スペクトルでの最適選択 | 未確定 | 前処理比較実験（LOB-CV） |
| U8 | 水ピーク内部標準 vs 硫酸ピーク内部標準の比較 | 未確定 | 培地組成依存性を評価 |

---

## 14. 出典リスト

| ID | タイトル | 出典 | 確度 |
|---|---|---|---|
| Abu-Absi 2011 | Real time monitoring of multiple parameters in mammalian cell culture bioreactors using an in-line Raman spectroscopy probe | DOI 10.1002/bit.23023 | 事実 |
| Whelan 2012 | In situ Raman spectroscopy for simultaneous monitoring of multiple parameters in mammalian cell culture bioreactors | DOI 10.1002/btpr.1572 | 事実 |
| Matthews 2016 | Closed loop control of lactate concentration in mammalian cell culture by Raman spectroscopy | DOI 10.1002/bit.26018 | 事実 |
| Berry 2015 | Cross-scale predictive modeling of CHO cell culture growth and metabolites using Raman spectroscopy | DOI 10.1002/btpr.2035 | 事実 |
| Santos 2018 | Monitoring mAb cultivations with in-situ Raman spectroscopy | DOI 10.1002/btpr.2635 | 事実 |
| Müller 2024 | Bioprocess in-line monitoring and control using Raman spectroscopy and Indirect Hard Modeling | DOI 10.1002/bit.28724 | 事実 |
| Graf 2022 | A Novel Approach for Non-Invasive Continuous InLine Control of Perfusion Cell Cultivations by Raman Spectroscopy | DOI 10.3389/fbioe.2022.719614 | 事実 |
| Baradez 2018 | Application of Raman Spectroscopy and Univariate Modelling As a Process Analytical Technology for Cell Therapy Bioprocessing | DOI 10.3389/fmed.2018.00047, PMID 29556497 | 事実 |
| Hsu 2020 | A single-cell Raman-based platform to identify developmental stages of human pluripotent stem cell-derived neurons | DOI 10.1073/pnas.2001906117, PMID 32694205 | 事実 |
| Costa 2024 | Harnessing Raman spectroscopy for cell therapy bioprocessing | DOI 10.1016/j.biotechadv.2024.108166 | 事実 |
| Polanco 2020 | Bioprocess Technologies that Preserve the Quality of iPSCs | DOI 10.1016/j.tibtech.2020.04.006 | 事実 |
| Isidro 2021 | Online monitoring of hiPSC expansion and hepatic differentiation in 3D culture by dielectric spectroscopy | DOI 10.1002/bit.27751 | 事実 |
| Manstein 2021 | High density bioprocessing of human pluripotent stem cells by metabolic control and in silico modeling | DOI 10.1002/sctm.20-0453, PMID 33660952 | 事実 |
| Borys 2021 | Overcoming bioprocess bottlenecks in large-scale expansion of hiPSC aggregates | DOI 10.1186/s13287-020-02109-4 | 事実 |
| Yang 2024 | In-line monitoring of bioreactor by Raman spectroscopy: direct use of a standard-based model through cell-scattering correction | J Biotechnol 396:41-52, DOI 10.1016/j.jbiotec.2024.10.007, PMID 39427757 | 事実 |
| Iversen 2014 | Raman spectroscopy for bioethanol: cell-scattering quadratic correction（Yang 2024 引用） | 論文参照 | 事実 |
| Klaverdijk 2025 | Single compound data supplementation to enhance transferability of fermentation specific Raman spectroscopy models | DOI 10.1007/s00216-025-05768-5 | 事実 |
| Dong 2024 | Improving Raman-Based Models for Real-Time Monitoring the CHO Cell Culture Process | DOI 10.3390/app14198890 | 事実 |
| Yan 2024 | Development of an in-line Raman analytical method for commercial-scale CHO cell culture | DOI 10.1002/biot.202300395 | 事実 |
| Rowland-Jones 2021 | Spectroscopy integration to miniature bioreactors and large scale production bioreactors | DOI 10.1002/btpr.3074 | 事実 |
| Machleidt 2024 | Feasibility and performance of cross-clone Raman calibration models in CHO cultivation | DOI 10.1002/biot.202300289 | 事実 |
| Pétillot 2020 | Calibration transfer for bioprocess Raman monitoring | DOI 10.1002/eng2.12230 | 事実 |
| Metze 2019 | Multivariate data analysis of capacitance frequency scanning for online monitoring of viable cell concentrations | DOI 10.1007/s00216-019-02096-3 | 事実 |
| Anderson 2022 | Capacitance spectroscopy enables real‐time monitoring of early cell death in mammalian cell culture | DOI 10.1002/biot.202200231 | 事実 |
| Rittershaus 2022 | N-1 Perfusion Platform Development Using a Capacitance Probe for Biomanufacturing | DOI 10.3390/bioengineering9040128 | 事実 |
| Pavurala 2025 | Cell culture media and Raman spectra preprocessing | PMCID PMC12954738 | 事実 |
| Saeys | Multivariate Calibration of Spectroscopic Sensors for Food Quality Evaluation（MSC/SNV/EMSC 解説） | https://lirias.kuleuven.be/retrieve/546668 | 事実 |
| Borg 2025 | Practical Insights into Multivariate Regression Models for Raman Spectroscopy | https://hal.science/hal-05441454/document | 事実 |
| Sigma AN9376 | N-1 Perfusion Raman Monitoring Application Note | https://www.sigmaaldrich.com/deepweb/assets/sigmaaldrich/marketing/global/documents/940/039/raman-perfusion-an9376-ms.pdf | 事実 |
| Sigma AN13446 | One-Batch Calibration for Cell Culture Raman | https://www.sigmaaldrich.com/deepweb/assets/sigmaaldrich/marketing/global/documents/174/174/an13446en-an-innovative-approach-to-streamline-raman-implementation-for-cell-culture-processes-one-batch-calibration-ms.pdf | 事実 |
| Thermo APN-0130 | MarqMetrix chemometric model transferability across 5 mammalian cell lines | https://documents.thermofisher.com/TFS-Assets/CAD/Application-Notes/marqmetrix-aoi-transfer-apn-0130-en.pdf | 事実 |
| bioprocesstools | How to Use Raman Spectroscopy for Real-Time Bioprocess Monitoring | https://bioprocesstools.com/blog/raman-spectroscopy-bioprocess-monitoring/ | 推定 |
| Metrohm AN-PAN-1065 | Inline monitoring of cell cultures with Raman spectroscopy | https://www.metrohm.com/en/applications/application-notes/prozess-applikationen-anpan/an-pan-1065.html | 事実 |
| Repligen MAVERICK | Instant Implementation of Raman-Based PAT | https://www.repligen.com/Products/analytics/maverick/Resources/DOC043_1.PDF | 事実 |
| StemCell mTeSR 3D manual | Expansion of Human Pluripotent Stem Cells as Aggregates in Suspension Culture | https://cdn.stemcell.com/media/files/manual/10000005520-Expansion_of_Human_Pluripotent_Stem_Cells_as_Aggregates_in_Suspension_Culture_Using_mTeSR_3D.pdf | 事実 |
| Eppendorf AN485 | hiPSC Aggregate Expansion in Stirred-tank Bioreactors | https://www.eppendorf.com/product-media/doc/en/11804882/Fermentors-Bioreactors_Application-Note_485_SciVario_Human-Induced-Pluripotent-Stem-Cell-hiPSC-Aggregate-Expansion-Stirred-tank-Bioreactors-SciVario-twin-Bioprocess-Controller.pdf | 事実 |
| ADR-0001 | Control architecture — thin LLM orchestrator over deterministic tools + Bayesian optimization | `docs/design/adr/0001-control-architecture.md` | 事実 |
| kg_bridge | KG → auto_cell 設計ブリッジ | `docs/design/kg_to_auto_cell.md` | 事実 |
| additional_raman | iPSC 浮遊/凝集体バイオリアクターにおける Raman 校正戦略 | `docs/design/ground_knowledge/additional_raman_calibration_ipsc.md` | 事実 |
| additional_integrated | 追加調査統合レポート | `docs/design/ground_knowledge/additional_investigation_integrated.md` | 事実 |

---

*本レポートは A 層（iPSC 浮遊/凝集体バイオリアクター制御）に限定。CHO/mAb 由来の数値を iPSC にそのまま転用しないことを明示。各主張には〔事実〕/〔推定〕/〔未確定〕/〔設計判断〕のラベルを付与した。*
