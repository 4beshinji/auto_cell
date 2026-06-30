# S02: iPSC CPP 閾値・シア・凝集体サイズ・CSPR に関する調査レポート

**対象**: auto_cell A 層（iPSC 浮遊凝集体バイオリアクター）の閉ループ制御  
**作成日**: 2026-06-30  
**ラベル規約**: 本文中の各数値主張の末尾に `〔事実〕` / `〔推定〕` / `〔未確定〕` を付与。

---

## 1. Executive Summary

iPSC 浮遊凝集体培養の CPP 包絡線は、CHO などの mAb プラットフォームと本質的に転用できない。本レポートでは、**Manstein & Zweigerdt 2021** の灌流攪拌槽モデル〔事実〕を中核に、**Borys 2021**（Vertical-Wheel の CFD/凝集体品質）〔事実〕、**Huang 2020**（動的灌流・動的攪拌スケールアップ）〔事実〕、**Odenwelder 2021**（iPSC の乳酸代謝）〔事実〕、**Nampe/Ghasemian**（攪拌とコルモゴロフスケール）〔事実〕などを統合し、A 層 `validate_tool_call` で用いる閾値・ランプ制限・CSPR の初期設計値を提示する。

**主要な不確実性**:

- **アンモニア**: iPSC ネイティブな毒性閾値は未確認。最も近い hESC データ（Chen 2010）は 5 mM まで影響なしを示すが、iPSC では細胞株・培地により変動する。〔未確定〕
- **CSPR**: iPSC 特異的な最適化研究はない。Manstein 2021 の高密度軌道と Huang 2020 の低密度軌道から概算すると **150–500 pL/cell/day** の作業範囲となる。〔推定〕
- **シア絶対値（Pa）**: iPSC 凝集体に対する安全な絶対シア応力閾値は確立されていない。代理指標として **コルモゴロフ長 λ と凝集体径分布**を監視すべき。〔未確定〕
- **ランプ制限値**: 現在の `kg_to_auto_cell.md` §4.0a の値は初期仮説であり、iPSC ランプ研究が存在しないため実機校正が必須。〔未確定/推定〕

---

## 2. CPP 閾値対照表（iPSC vs CHO）

| 項目 | iPSC 値（A 層設計値） | CHO 値（代表例） | 根拠 | 確信度 |
|---|---|---|---|---|
| **pH 目標/制限** | 7.1 / 6.9–7.3 | 7.0–7.2（pH <6.8 または >7.6 で成長低下） | Manstein 2021; Xu 2023 | iPSC: 事実 / CHO: 事実 |
| **DO 目標/制限** | 40 % → 10 % / 5–50 % | 20–60 % | Manstein 2021; Fleischaker 1981; Li 2022 | iPSC: 事実 / CHO: 事実 |
| **乳酸 Warning/Limit** | ≥35 mM / <50 mM | ~60 mM（細胞株依存） | Manstein 2021 (K_Lac=50 mM); Lao & Toth 1997 | iPSC: 推定 / CHO: 事実 |
| **アンモニア Warning/Limit** | <3 mM / <5 mM（監視値） | ~5 mM（密度 10% 低下）、10 mM で糖鎖変化 | Chen 2010 (hESC); Xing 2008 | iPSC: 未確定 / CHO: 事実 |
| **浸透圧 Warning/Limit** | <450 / <500 mOsm/kg | 標準 280–320、>400 で高浸透圧ストレス | Manstein 2021; Chaudhry 2009 (mESC); Li 2022 | iPSC: 推定 / CHO: 事実 |
| **グルコース下限** | >1.8 mM (>1.5 mM Limit) | 2–4 g/L ≈ 11–22 mM（プロセス依存） | Manstein 2021 (K_Glc=1.5 mM) | iPSC: 事実 / CHO: 事実 |
| **グルタミン下限** | >0.01 mM (>0.005 mM Limit) | 培地依存（通常 2–4 mM 初期、枯渇回避） | Manstein 2021 (K_Gln=0.01 mM) | iPSC: 事実 / CHO: 事実 |
| **攪拌 rpm** | 50–120 rpm（Limit 30–150） | プロセス・機器依存（通常 50–200 rpm 級） | Borys 2021; Manstein 2021 | iPSC: 推定 / CHO: 事実 |
| **凝集体平均径** | 150–350 µm / >400 µm Limit | 単一懸濁（該当なし） | Manstein 2021; Borys 2021; Huang 2020 | iPSC: 推定 |
| **大径凝集体（>400 µm）割合** | <10 %（Warning >15 %、Limit >20 %） | 該当なし | Borys 2021; Huang 2020 | iPSC: 推定 |
| **灌流率** | 0 → 7 vvd（条件付き） | 0 → 数 vvd（抗体プロセスで 1–3 vvd 級） | Manstein 2021; Huang 2020 | iPSC: 事実 |
| **CSPR** | 0.15–0.50 nL/cell/day（=150–500 pL/cell/day） | 20–75 pL/cell/day（抗体灌流の典型） | Manstein 2021; Huang 2020; CHO レビュー | iPSC: 未確定 / CHO: 事実 |
| **温度** | 37 ℃ / 36–38 ℃ | 37 ℃（生産段階で 32–37 ℃） | 標準培養条件 | 事実 |
| **無菌性** | 逸脱ゼロ/汚染検知で停止 | 同上 | GMP/規制一般 | 事実 |

### 2.1 各パラメータの解説

#### 乳酸（Lactate）

- Manstein 2021 の in silico モデルでは **K_Lac = 50 mM**、最大比増殖速度に対する阻害係数として扱われる。〔事実〕
- Odenwelder 2021 は K3 iPSC を用いた 13C-MFA で、**20 mM 乳酸**存在下でも増殖が阻害されず、乳酸を基質として利用できることを示した。〔事実〕
- したがって A 層では **Warning 35 mM / Limit 50 mM** を採用するが、これは Manstein モデルの仮定に依存しており、細胞株により変動する。〔推定〕

#### アンモニア（Ammonia）

- iPSC 凝集体培養における系統的なアンモニア毒性試験は見つからなかった。〔未確定〕
- Chen 2010（hESC、2D/マイクロキャリア）では **5 mM NH4+ まで増殖に影響なし**を報告。〔事実〕
- 哺乳動物細胞一般では 2–10 mM で感受性が大きく変動（Hassell 1991）〔事実〕。
- 現時点では **Warning 3 mM / Limit 5 mM** とし、細胞株特異的な閾値決定を保留する。〔推定/未確定〕

#### 浸透圧（Osmolality）

- Manstein 2021 は **K_Osm = 500 mOsm/kg** を採用し、高 VCD 灌流でも osmolality ピークを抑制。〔事実〕
- Chaudhry 2009（mESC）では **400 mOsm/kg** で EB 形成能が約 3 倍低下、**500 mOsm/kg** でさらに低下。〔事実〕
- A 層では **Warning 450 / Limit 500 mOsm/kg** を採用。〔推定〕

#### pH / DO

- Manstein 2021: pH 7.1、DO 40 % → 10 %（時間経過に伴い低下）〔事実〕。
- Huang 2020: pH 7.2、DO 50 % を採用し、10 %/90 % は増殖にやや不利。〔事実〕
- CHO レビューでは pH 6.8 未満/7.6 超で成長低下、DO 20–60 % が一般的。〔事実〕

---

## 3. ランプ制限値の定量的根拠

`kg_to_auto_cell.md` §4.0a に記載の値は **初期仮説**であり、iPSC 特異的なランプ試験は存在しない。〔未確定〕 以下、文献に基づく検討と推奨値を示す。

| アクチュエータ | 現在の設計値（§4.0a） | 文献アンカー | 推奨暫定値（校正前） | 備考 |
|---|---|---|---|---|
| `set_perfusion_rate` | ±0.5 vvd / 30 min | Huang 2020: pH 6.8 到達後、前日セットポイント比 **+30 %/day**（0.5 vvd 起点で +0.15 vvd/day）; Manstein: day 5 で 1→2 vvd 程度の段階増加 | **±0.25 vvd / h**（≦±6 vvd/day） | 現在値は文献より 1–2 桁急峻。〔推定〕 |
| `set_agitation_rpm` | ±20 rpm / 5 min | Huang 2020: day0→day2 で **75→80→85 rpm（+5 rpm/day）**; Borys 2021: 40/60/80 rpm を固定条件で比較 | **±5 rpm / h**（≦±0.4 rpm/5 min） | 急激な rpm 変更は凝集体破砕/ショックリスク。〔推定〕 |
| `set_gas_setpoint(DO)` | ±5 % / 5 min | Manstein 2021: DO 40 % → 10 % を数日間で漸減 | **±5 % / h** | ガス切替ショック回避。〔推定〕 |
| `set_gas_setpoint(pH/CO₂)` | ±0.1 / 5 min | Chaudhry 2009: pH 影響は 24–48 h の曝露で顕在化 | **±0.05 pH / h** | 過度な CO₂ 変化は pCO₂/osmolality へ波及。〔推定〕 |

### 3.1 なぜ「ゆるやかなランプ」が必要か

1. **浸透圧ショック**: 灌流率を急激に上げると、培地成分濃度の急変・osmolality 変動が起こり、凝集体内外の浸透圧勾配が細胞にストレスを与える。〔推定〕
2. **シアストレス**: 攪拌 rpm を急変させると、凝集体は一時的に高シア領域（インペラ近傍）に滞留したり、集合体同士の衝突が増加し、凝集体破砕や細胞死を招く。〔推定〕
3. **pH/DO ショック**: ガス組成の急変は、培養液中の CO₂/O₂ 溶解平衡を崩し、細胞外 pH やミトコンドリア酸化に急な負荷をかける。〔推定〕

### 3.2 暫定方針

- **フェーズ 1（CSV 出荷前）**: 上表の推奨暫定値で実装し、ゲート条件で実証する。
- **フェーズ 2**: 対象細胞株・機器でランプ応答試験を行い、±Δ をベイズ最適化または DOE で更新する。
- **イベント連動**: `lactate_high`/`glucose_low`/`osmolality_high` などが発火しても、1 サイクルで目標値に到達しようとせず、数時間〜 1 日の勾配で接近する。

---

## 4. 凝集体径 ↔ 品質の相関

### 4.1 酸素・栄養拡散限界

- 組織内の酸素拡散限界は約 **100–200 µm** とされる（Chen 2014）〔事実〕。しかし、凝集体は球状ではなくサイズ分布を持つため、**平均径 300 µm** でも表面近傍細胞が大半を占め、中心壊死は必ずしも生じない。
- Borys 2021 は水平翼バイオリアクターで **>400 µm** に達すると中心部の壊死リスクが高まると報告。〔事実〕
- Huang 2020 は収穫時の **平均凝集体径 ≈300 µm** を上限目標とし、VCD 1–2×10⁶ cells/mL で継代を実施。〔事実〕

### 4.2 凝集体径分布の管理指標

| 指標 | 目標/Warning/Limit | 根拠 | 確信度 |
|---|---|---|---|
| 平均径 | 150–350 µm / >350 µm Warning / >400 µm Limit | Manstein K_Agg=175 µm; Huang ~300 µm; Borys >400 µm 壊死リスク | 推定 |
| >400 µm 割合 | <10 % / >15 % / >20 % | Borys 2021 代理指標 | 推定 |
| 分布幅（標準偏差） | 小さいほど均一 | Nampe 2017; Ghasemian 2020 | 推定 |

### 4.3 シア指標：rpm ではなくコルモゴロフスケール

iPSC 凝集体に対する安全な絶対シア応力（Pa）閾値は確立されていない。〔未確定〕 そのため、以下の代理指標を併用する。

- **コルモゴロフ長 λ**:
  - Ghasemian 2020 の CFD では、スピナーフラスコで 40 rpm 時の平均 λ ≈ 464 µm、100 rpm 時 ≈ 149 µm。〔事実〕
  - 同一研究で、H9-hESC / RIV9-hiPSC の平均凝集体径はいずれの rpm でも平均 λ を超えなかった。〔事実〕
  - これは λ が凝集体サイズを「制御しうる」ことを示唆するが、必ずしも「制限」ではない。〔推定〕
- **Croughan 1987 の経験則**:
  - マイクロキャリア培養で **λ < 2/3 粒子径**（約 125 µm）で成長率が低下、λ < 1/2 粒子径（約 100 µm）で顕著な障害。〔事実〕
  - iPSC 凝集体への直接的適用は未検証。〔未確定〕

### 4.4 品質指標との対応

- Borys 2021: Vertical-Wheel で 40–80 rpm の範囲では、増殖率・プラリポテンシー指標に大きな差はなかったが、**水平翼リアクターでは >400 µm 凝集体で不均一性と壊死リスク**。〔事実〕
- Huang 2020: ESI-017（hESC）と NCRM1（iPSC）で、凝集体形成速度・初期凝集体径に有意差あり、プロセス転換時に day 1 凝集体径が重要な変動要因。〔事実〕
- 結論:**平均径だけでなく >400 µm 割合・分布幅・細胞株固有の day 1 凝集挙動を監視する**。〔推定〕

---

## 5. CSPR（Cell-Specific Perfusion Rate）の実用範囲

### 5.1 定義

```
CSPR [nL/cell/day] = perfusion_rate [vvd] × 1000 [µL/mL] / (VCD [10⁶ cells/mL] × 10⁶ [cells/mL])
                   = perfusion_rate / VCD [10⁶ cells/mL]  [nL/cell/day]
```

簡略化例: 1 vvd @ 1×10⁶ cells/mL → **1 nL/cell/day = 1000 pL/cell/day**。

### 5.2 文献からの概算

| プロセス | VCD | 灌流率 | CSPR | 根拠 |
|---|---|---|---|---|
| Manstein 2021（高密度灌流） | 35×10⁶ cells/mL | 7 vvd | **200 pL/cell/day** | Manstein 2021 Table 3〔事実〕 |
| Huang 2020 固定灌流 | ~1×10⁶ cells/mL | 0.5 vvd | **500 pL/cell/day** | Huang 2020〔事実〕 |
| Huang 2020 動的灌流 | ~1–2×10⁶ cells/mL | 0.5 → 1.1 vvd | **250–500 pL/cell/day** | Huang 2020〔推定〕 |
| CHO 抗体灌流（参考） | 20–60×10⁶ cells/mL | 1–3 vvd | **20–75 pL/cell/day** | 産業レビュー〔事実〕 |

### 5.3 A 層での推奨範囲

- **暫定作業範囲**: **150–500 pL/cell/day**（= 0.15–0.50 nL/cell/day）〔推定〕
- **下限**: 栄養・成長因子・温度不安定成分の供給が不足しないこと。低密度（<1×10⁶ cells/mL）では 0.5 vvd でも 500 pL 級となり十分。〔推定〕
- **上限**: 培地コスト・osmolality 上昇・廃棄物希釈効率の観点から、高密度では 7 vvd（Manstein）に対応する 200 pL 程度を超えない方が望ましい。〔推定〕
- **注意**: CHO の 20–75 pL/cell/day は iPSC には転用不可。iPSC は抗体生産細胞よりも成長因子・タンパク質要求量が高く、凝集体拡散制限がある。〔事実：kg_to_auto_cell.md §4〕

---

## 6. 細胞株・培地による変動性

### 6.1 細胞株差

- Huang 2020: ESI-017（hESC）と NCRM1（iPSC）で、特定増殖率・乳酸収率・プラリポテンシーに差はなかったが、**day 1 凝集体径**（74.9 µm vs 92.4 µm）と凝集体成長速度に差あり。〔事実〕
- このため、同一プロトコルを別細胞株に転換する際は、**初期凝集・撹拌プロファイルを再調整**する必要がある。〔推定〕

### 6.2 培地差

- Odenwelder 2021: K3 iPSC は **乳酸を代謝基質**として利用できる。〔事実〕
- Manstein 2021: 高密度灌流モデルは特定培地・添加因子を前提とする。〔事実〕
- mTeSR1、E8、StemFlex、化学成分確定培地などでは、乳酸・アンモニア・浸透圧耐性が変動する可能性がある。〔推定〕

### 6.3 温度・pH・DO 相互作用

- Chaudhry 2009: mESC で pH と osmolality の相互作用が EB 形成能に強く影響。〔事実〕
- Hassell 1991: アンモニア毒性は乳酸濃度と相互作用し、乳酸 >12 mM でアンモニア 1–4 mM の協奏的阻害が生じる。〔事実〕
- したがって CPP は単独閾値ではなく、**多変量イベント**として扱う必要がある。〔推定〕

---

## 7. 不確実性と実験計画

### 7.1 未確定事項（優先順）

1. **iPSC 凝集体におけるアンモニア毒性閾値**（mM オーダー）。
2. **細胞株ごとの乳酸 K_Lac**（50 mM が普遍か）。
3. **凝集体径分布とプラリポテンシー・分化能・カリオタイプの定量相関**。
4. **iPSC 特異的 CSPR 最適値**（150–500 pL/cell/day の範囲内で最小培地コスト条件）。
5. **ランプ制限値の実証**（特に灌流率・攪拌 rpm）。
6. **Vertical-Wheel vs 攪拌槽のシア包絡線**（同じ rpm でも λ 分布が異なる）。

### 7.2 推奨 DOE（DASbox / ambr®15 スケール）

#### A. 代謝閾値探索（2–3 週間/マトリクス）

| 因子 | レベル | 測定 |
|---|---|---|
| 乳酸（添加） | 10, 20, 35, 50, 65 mM | VCD, viability, Oct3/4/Sox2/SSEA-4/Tra-1-60, lactate/glucose |
| アンモニア（添加） | 0, 1, 3, 5, 10 mM | 同上 + pH, osmolality |
| 浸透圧（NaCl 調整） | 300, 400, 450, 500, 550 mOsm/kg | 同上 + aggregate size |
| 乳酸×アンモニア | 中央点含む full/fractional factorial | 相互作用評価 |

#### B. シア・凝集体サイズ探索

| 因子 | レベル | 測定 |
|---|---|---|
| 攪拌 rpm | 40, 60, 80, 100, 120 rpm（機器許容内） | Aggregate size distribution, viability, pluripotency, karyotype |
| ランプ速度 | 5 rpm/h, 20 rpm/h, 即刻 | 上記 + lactate dehydrogenase release |
| CFD 連携 | 各 rpm の λ 分布を事前計算 | λ vs 平均径・>400 µm 割合の相関 |

#### C. 灌流・CSPR 最適化

| 因子 | レベル | 測定 |
|---|---|---|
| 固定灌流 | 0.3, 0.5, 1.0, 2.0, 3.0 vvd @ 1–2×10⁶ cells/mL | VCD, viability, metabolites, pluripotency |
| 動的灌流 | pH 6.8 トリガ、+20 %/day、+30 %/day | 同上 + osmolality peak |
| 高密度 CSPR | 35×10⁶ cells/mL 到達時の灌流率を 3, 5, 7 vvd | 同上 + medium utilization |

#### D. 品質ゲート

すべての条件で以下を必須とする。

- Viability ≥ 90 %（day 5–7）
- 4-marker pluripotency（Oct3/4, Sox2, SSEA-4, Tra-1-60）≥ 90 %
- 正常カリオタイプ
- 凝集体平均径 < 350 µm、>400 µm 割合 < 15 %
- トリリニージ分化能（Borys 2021 準拠）

### 7.3 解析・フィードバック

- 取得データから **Monod/K_S パラメータ**を再推定し、`plant_model` の定数を更新する。
- ランプ試験から `validate_tool_call` の `ramp_limit` を確定する。
- 不確実性を明示し、**次回 CPP レビュー**（S03）で再検討する。

---

## 8. 結論・A 層実装への示唆

1. **Manstein 2021 の 6 定数（K_Glc, K_Lac, K_Gln, K_Osm, K_Agg, µ）**は A 層 `plant_model` の出発点として堅牢。〔事実〕
2. **アンモニア**は iPSC ネイティブ閾値が未確定のため、監視値（3 mM Warning / 5 mM Limit）を暫定とし、速やかな DOE を要する。〔未確定〕
3. **CSPR** は 150–500 pL/cell/day の範囲で運用し、細胞株・密度で再校正する。〔推定〕
4. **シア管理**は rpm 単独では不十分。λ（コルモゴロフ長）と凝集体径分布、特に **>400 µm 割合**を監視する。〔推定〕
5. **ランプ制限値**は現行 §4.0a よりも保守的に設定することを推奨（特に攪拌・灌流）。実機校正を必須とする。〔推定/未確定〕
6. **細胞株・培地変動**は大きいため、CPP 包絡線は「検証済み固定値＋イベント駆動の保守的ランプ」として扱い、LLM/ベイズ最適化による自動探索は CSV 後段に留める。〔推定〕

---

## 9. 参考文献

1. **Manstein F, Ullmann C, Triebert W, Zweigerdt R.** High density bioprocessing of human pluripotent stem cells by metabolic control and in silico modeling. *Stem Cells Transl Med.* 2021;10(7):1063-1080. DOI:10.1002/sctm.20-0453; PMID:33660952; PMCID:PMC8235132.
2. **Manstein F, Zweigerdt R.** In silico model and protocol for high-density hPSC perfusion culture. *STAR Protocols.* 2021;2(4):100988. DOI:10.1016/j.xpro.2021.100988; PMCID:PMC8666714.
3. **Borys BS, Cahan P, Truitt Z, Rancourt DE, Kallos MS.** Overcoming bioprocess bottlenecks in large-scale expansion of hiPSC aggregates in vertical-wheel bioreactors. *Stem Cell Res Ther.* 2021;12:55. DOI:10.1186/s13287-020-02109-4; PMID:33436078; PMCID:PMC7805206.
4. **Huang S, Pigeau G, Csaszar E, Dulgar-Tulloch A.** Process development and scale-up of pluripotent stem cell manufacturing. *Cell Gene Ther Insights.* 2020;1(1). DOI:10.18063/cgti.v1.i1.1784.
5. **Odenwelder DC, Lu X, Harcum SW.** Induced pluripotent stem cells can utilize lactate as a metabolic substrate to support proliferation. *Biotechnol Prog.* 2021;37(2):e3090. DOI:10.1002/btpr.3090; PMID:33029909.
6. **Nampe D, Kallos MS, Miki H, et al.** Impact of fluidic agitation on human pluripotent stem cells in stirred suspension culture. *Biotechnol Bioeng.* 2017;114(9):2109-2120. DOI:10.1002/bit.26334; PMID:28480972.
7. **Ghasemian M, Layton C, Nampe D, zur Nieden NI, Tsutsui H, Princevac M.** Hydrodynamic characterization within a spinner flask and a rotary wall vessel for stem cell culture. *Biochem Eng J.* 2020;160:107533. DOI:10.1016/j.bej.2020.107533.
8. **Chen X, Chen A, Woo TL, Choo ABH, Reuveny S, Oh SKW.** Investigations into the metabolism of two-dimensional colony and suspended microcarrier cultures of human embryonic stem cells in serum-free media. *Stem Cells Dev.* 2010;19(11):1781-1792. DOI:10.1089/scd.2010.0077.
9. **Chaudhry MA, Bowen BD, Piret JM.** Culture pH and osmolality influence proliferation and embryoid body yields of murine embryonic stem cells. *Biochem Eng J.* 2009;45(2):126-135. DOI:10.1016/j.bej.2009.03.005.
10. **Croughan MS, Hamel JF, Wang DIC.** Hydrodynamic effects on animal cells grown in microcarrier cultures. *Biotechnol Bioeng.* 1987;29(1):130-141. DOI:10.1002/bit.260290117.
11. **Lao MS, Toth D.** Effects of ammonium and lactate on growth and metabolism of a recombinant Chinese hamster ovary cell culture. *Biotechnol Prog.* 1997;13(5):688-691. DOI:10.1021/bp9602360; PMID:9336989.
12. **Xing Z, Li Z, Chow V, Lee SS.** Identifying inhibitory threshold values of repressing metabolites in CHO cell culture using multivariate analysis methods. *Biotechnol Prog.* 2008;24(3):675-683. DOI:10.1021/bp070466m.
13. **Li ZM, et al.** Factors affecting the expression of recombinant protein and improvement strategies in Chinese hamster ovary cells. *Front Bioeng Biotechnol.* 2022;10:880155. DOI:10.3389/fbioe.2022.880155.
14. **Xu WJ, et al.** Progress in fed-batch culture for recombinant protein production by CHO cells. *Front Bioeng Biotechnol.* 2023;11:1101702. DOI:10.3389/fbioe.2023.1101702; PMCID:PMC9843118.
15. **Chen KG, Mallon BS, McKay RDG, Robey PG.** Human pluripotent stem cell culture: considerations for maintenance, expansion, and therapeutics. *Cell Stem Cell.* 2014;14(1):13-26. DOI:10.1016/j.stem.2013.12.005.
16. **Hassell T, Gleave S, Butler M.** Growth inhibition in animal cell culture: the effect of lactate and ammonia. *Appl Biochem Biotechnol.* 1991;30(1):29-41. DOI:10.1007/BF02922022; PMID:1952924.
17. **Wurm FM.** Production of recombinant protein therapeutics in cultivated mammalian cells. *Nat Biotechnol.* 2004;22(11):1393-1398. DOI:10.1038/nbt1026; PMID:15529155.
18. **Fleischaker RJ, Sinskey AJ.** Oxygen demand and supply in cell culture. *Eur J Appl Microbiol Biotechnol.* 1981;12(4):193-197. DOI:10.1007/BF00499486.
