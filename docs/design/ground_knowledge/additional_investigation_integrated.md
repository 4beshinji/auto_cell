# 追加調査統合レポート

> **担当**: 追加調査統合エージェント  
> **Scope**: auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御、Manstein 型灌流 0→7 vvd）  
> **Date**: 2026-06-16  
> **前提**: ADR-0001（L0 局所 PID + L1 決定的レシピ/ルール + L2 ベイズ最適化 + L3 薄い LLM オーケストレータ）、R&D 一次、Human-on-the-loop  

---

## 目次

1. [Executive Summary](#1-executive-summary)
2. [MPC for iPSC 浮遊灌流](#2-mpc-for-ipsc-浮遊灌流)
3. [PINN/デジタルツイン](#3-pinnデジタルツイン)
4. [Raman 校正戦略](#4-raman-校正戦略)
5. [CHO → iPSC CPP 転換](#5-cho--ipsc-cpp-転換)
6. [PIC/S Annex 22 ロードマップ](#6-pics-annex-22-ロードマップ)
7. [浮遊凝集体画像解析](#7-浮遊凝集体画像解析)
8. [統合ロードマップ（v1/Phase2/Phase3）](#8-統合ロードマップv1phase2phase3)
9. [未解決事項](#9-未解決事項)
10. [トレーサビリティ](#10-トレーサビリティ)

---

## 1. Executive Summary

本レポートは、6 つの追加調査ドメイン（MPC、PINN/DT、Raman、CHO→iPSC CPP、PIC/S Annex 22、浮遊凝集体画像解析）の結果を統合し、A 層設計への統一的な提言をまとめるものである。各ドメインの個別レポートと KG 差分は、それぞれ `docs/design/ground_knowledge/additional_*.md` および `docs/knowledge_graph/generated/additional_*_kg_diff.json` に記載されている。

### 1.1 主要結論

1. **CHO 由来の数値・戦略を iPSC にそのまま転用しない**〔設計判断〕。乳酸閾値、アンモニア閾値、浸透圧上限、攪拌 rpm、灌流率、mAb タイトル目的関数は、iPSC 浮遊凝集体の代謝・品質特性と整合しない。
2. **v1（Phase 1）の制御コアは L1 決定的レシピ/ルールのまま**〔推定：ADR-0001〕。MPC、PINN/DT、Raman 閉ループ、DL 品質代理指標は、iPSC 実証不足・データ不足のため v1 では導入しない。
3. **Human-on-the-loop は全将来技術の前提**〔設計判断〕。包絡線外 setpoint、BO 提案、MPC 提案軌道、低信頼度 AI 出力は研究者承認を必須とする。
4. **ADR-0001 の L0-L3 分離は PIC/S Annex 22 と本質的に整合**〔推定〕。L0/L1 は決定的、L2 BO/GP は静的モデルとして扱える、L3 LLM は非クリティカル用途に限定する設計を維持する。
5. **データ要件は現実的に段階的**〔推定〕。Hybrid ODE+NN は 50–100 バッチ、Raman PLS は 5–15 バッチ、凝集体 DL 品質代理指標は数十〜数百バッチの offline 正解ラベルが必要。R&D 一次では 5–10 run から運用を開始する可能性が高い。

### 1.2 矛盾・重複・欠落の検出

| 項目 | 検出結果 | 対応 |
|---|---|---|
| **CHO 数値の iPSC 転用** | MPC（Rashedi 2022）の「抗体タイトル 2% 向上・グルコース 35% 増加」、Raman（Yokogawa）の「glucose RMSEP 0.23 g/L」、BO（Bioprocess Intl 2026）の「mAb 生産性 25% 向上」などが iPSC 文脈で引用されている。 | 全ドメインで「iPSC 目的関数・品質指標に再定義」または「再校正必須」と明記。棄却リスト化（§5.4）。 |
| **導入フェーズの矛盾** | MPC レポートは Phase 2 から MPC シミュレーション、PINN/DT レポートは Phase 2 から Hybrid ODE+NN PoC、Raman レポートは v1.5/Phase 2 からアドバイザリ入力、画像解析レポートは v1 で at-line 画像を必須とする。 | Phase 1 は全技術で「観測・計画・基盤」、Phase 2 は「MPC シミュレーション + Hybrid ODE+NN PoC + Raman アドバイザリ + 画像定量化」、Phase 3 は「閉ループ化・経済最適化」に統一（§8）。 |
| **Annex 22 との整合** | PINN/DT/MPC の一部は動的・確率的要素を含みうる。 | Critical 制御経路は L1 決定的コアに留め、AI/ML は非クリティカル/アドバイザリに限定。静的・決定論的証明を Phase 2 から準備（§6）。 |
| **ノード ID の重複** | KG 差分間で `src_yang_2024` が 2 件出現（PINN/DT と Raman）。内容は別論文（DOI 10.1021/acs.iecr.4c01459 vs 10.1016/j.jbiotec.2024.10.007）。 | 統合 KG 差分で `src_yang_2024_pinn` / `src_yang_2024_raman` にリネームして解消。〔事実：KG 差分検証〕 |
| **欠落** | iPSC ネイティブのアンモニア閾値、シア応答の定量式、凝集体径分布と品質の相関、Raman 光散乱補正の iPSC 固有パラメータ、PINN 構造、DL 品質代理指標の実証が不足。 | §9 に未解決事項として集約し、調査継続または実験決定とする。 |

### 1.3 優先度 5 段階の概要

| 優先度 | 含まれる項目 |
|---|---|
| **v1 必須** | L1 決定的レシピ/ルール、Manstein ODE plant_model、Nova FLEX2 at-line、at-line 凝集体画像、ALCOA-lite 監査ログ、Human-on-the-loop 承認、意図用途文書テンプレート。 |
| **Phase 2（12–24 ヶ月）** | MPC シミュレーション（perfusion rate 単一 MV）、GP バイアス補正 / Hybrid ODE+NN PoC、Raman PLS アドバイザリ入力（5+ バッチ校正後）、画像定量化・形態メトリクス、静的決定論的 AI の技術的統制。 |
| **Phase 3（24–48 ヶ月）** | 多変数適応 MPC、Hybrid DT + advisory MPC、Raman 閉ループ入力（10+ バッチ・光散乱補正後）、DL 品質代理指標の BO 統合、GAMP IQ/OQ/PQ 移行。 |
| **調査継続** | iPSC 固有アンモニア閾値、凝集体光散乱補正、PINN 構造、DL 品質代理指標実証、シア定量指標、BO 目的関数重み。 |
| **棄却** | CHO 由来数値の iPSC 直接転用、2D confluency の凝集体適用、LLM/生成 AI による Critical 制御、動的/確率的 AI の Critical 用途。 |

---

## 2. MPC for iPSC 浮遊灌流

### 2.1 現状と結論

- **iPSC 浮遊凝集体培養への MPC 直接実証例は本調査で確認できなかった**〔未確定/事実：Web 検索・文献サーベイ〕。
- 最も近い領域は、**MSC 培養での乳酸ベース適応 DARX-MPC**（Van Beylen et al. 2020）であり、R² 99.80% ± 0.02%（同実験データ）、未知トリプリケートで平均 96.57% の適合を示した〔事実：DOI 10.3390/bioengineering7030078〕。
- **PSC 動的灌流**（Huang et al. 2020）は pH 6.8 到達をトリガーに perfusion rate を 30%/日で ramp させ、固定灌流と比較して day 6 で平均 25% の高密度化、乳酸 15 mM 未満抑制を達成した〔事実：DOI 10.18063/cgti.v1.i1.1784〕。このルールベース動的戦略を MPC で多変数化・最適化できる〔推定〕。
- **Manstein & Zweigerdt 2021** は 7 日で 35×10⁶ cells/mL（70 倍拡大）を達成し、Berkeley-Madonna in silico モデルで灌流率 1→2 vvd、グルコース濃度 3.15→7.65 g/L、80 rpm 撹拌等を最適化した〔事実：DOI 10.1002/sctm.20-0453〕。この plant_model は MPC の内部モデル候補となる〔推定〕。

### 2.2 CHO/mAb 由来実績の転用禁止

- Rashedi et al. (DYCOPS-2022) は Amgen の fed-batch CHO で線形 MPC を実機適用し、最終タイトル 2% 向上、グルコース投与量 35% 増加、タンパク質純度改善を報告した〔事実：DYCOPS-2022 paper 0202〕。しかし、これらの数値は iPSC 製品（未分化マーカー維持・凝集体品質）には直接当てはまらない〔事実〕。

### 2.3 定式化案

A 層 iPSC 浮遊灌流（Manstein 型）での MPC 定式化案〔推定〕：

| 要素 | 候補 | 備考 |
|---|---|---|
| 状態 x | VCD, viability, glucose, lactate, glutamine, osmolality, aggregate diameter, DO, pH | glucose/lactate は in-line Raman または at-line Nova；VCD は capacitance；凝集体径は at-line 画像 |
| 操作変数 u | Perfusion rate (vvd), 必要に応じ glucose/glutamine bolus feed | 主レバーは灌流率 |
| 外乱 w | 細胞株特異的成長率、凝集体形成動態、温度ラボジット | 適応更新で吸収 |
| 制約 g(x,u) | 0 ≤ perfusion ≤ 7 vvd; glucose > 1.5 mM; lactate < 50 mM; osmolality < 500 mOsm/kg; aggregate 150–350 µm; pump rate ramp ≤ 0.5 vvd/30 min | CPP 包絡線（Manstein 2021） |
| 目的関数 J | VCD 到達・生存率・未分化マーカー維持・培地コスト・乳酸抑制の多目的/重み付き | 品質項は offline/run 単位で検証 |

### 2.4 導入ロードマップ

| フェーズ | 内容 | Human-on-the-loop |
|---|---|---|
| **v1 / Phase 1** | MPC は導入しない。L1 決定的ルールで灌流率を glucose/lactate/osmolality トリガーで条件起動。plant_model を将来 MPC の内部モデル候補として整備。 | 包絡線外 setpoint・trigger_passage・BO 提案を承認。 |
| **Phase 2** | plant_model（Manstein ODE）または線形化データ駆動モデルを用いた MPC シミュレータ構築。perfusion rate のみを最適化。CasADi + do-mpc または acados。 | MPC 提案軌道を HMI で提示、研究者が承認/調整後に L1 へ反映。 |
| **Phase 3** | perfusion rate + glucose/glutamine bolus feed + agitation setpoint の多変数 MPC。Raman/Nova/capacitance からの適応更新。経済 MPC（Economic MPC）で培地コスト・培養時間を統合。 | MPC 提案、DT ベース異常検知の承認。 |

### 2.5 出典

| ID | タイトル | URL/DOI | 確度 |
|---|---|---|---|
| Manstein 2021 | Manstein & Zweigerdt 2021 | DOI 10.1002/sctm.20-0453; PMC8666714 | 事実 |
| Huang 2020 | Process development and scale-up of PSC manufacturing | DOI 10.18063/cgti.v1.i1.1784 | 事実 |
| Van Beylen 2020 | Lactate-Based MPC for Cell Therapy | DOI 10.3390/bioengineering7030078 | 事実 |
| Rashedi 2022 | MPC Design for Bioprocesses (DYCOPS-2022) | https://skoge.folk.ntnu.no/prost/proceedings/dycops-2022/files/0202.pdf | 事実 |

---

## 3. PINN/デジタルツイン

### 3.1 現状と結論

- **iPSC 浮遊灌流プロセスへの PINN/ハイブリッド DT 適用は、現時点で産業実証例が極めて少ない**〔事実：文献サーベイ〕。文献のほとんどは CHO fed-batch または微生物培養であり、iPSC 凝集体培養にそのまま転用できない。
- **auto_cell の現行 plant_model（Manstein 2021 ベース 6 項 Monod ODE）は、Phase 1 で十分に機能する決定的検証リグ**である〔推定：ADR-0001; alignment_with_downloaded_report.md〕。
- **データ要件**: hybrid ODE+NN で 50–100 バッチ、純粋 NN で 200–500 バッチ、PINN で 30–80 バッチとされるが、これらは CHO/microbial 基準であり iPSC では同等以上が必要〔推定：Bioprocesstools 2026 サーベイ〕。
- **不確実性定量化**: Bayesian PINN、Deep Ensemble、EFI 等が存在するが、iPSC 培養への検証は未確定。Human-on-the-loop には「高不確実性時は人へエスカレーション」が必須〔推定：Shih et al. 2025〕。

### 3.2 産業例の転用注意

- **Yang et al. 2024**: 大規模パイロット CHO fed-batch に PINN ハイブリッドモデルを適用〔事実：DOI 10.1021/acs.iecr.4c01459〕。モデル構造は参考だが、パラメータ・損失関数・状態変数は iPSC 用に再設計が必要〔推定〕。
- **Thirugnanasambandam et al. 2025**: 汎用バイオリアクター向け dual-ANN PINN。時変制御入力を伴う高次元状態の複雑問題では長期外挿で性能が著しく低下〔事実：DOI 10.1016/j.compchemeng.2025.109354〕。iPSC 灌流はまさに該当するため訓練ドメイン外予測は信用できない〔推定〕。
- **Yokogawa Insilico Biotechnology**: mAb 製造（CHO 等）中心。iPSC 浮遊凝集体の凝集体形成動力学・未分化性品質指標はカバーしていない〔推定〕。

### 3.3 plant_model からの拡張路線

```
Phase 1: Manstein ODE（決定的、文献値固定）
   ↓ 実 run データ蓄積
Phase 2: ベイズパラメータ同定 / GP バイアス補正
   ↓ 50+ run 蓄積
Phase 3: Hybrid ODE + NN（一部 kinetic term を NN で置換）
   ↓ 100+ run 蓄積・検証完了
Phase 4: PINN / Digital Twin（物理損失 + データ損失、不確実性付き）
```

### 3.4 不確実性定量化の推奨

| 手法 | 長所 | 短所 | 推奨度 |
|---|---|---|---|
| GP バイアス補正 | 既存 BO インフラと統合しやすい | 低 run 数では表現力に限界 | Phase 2 推奨 |
| Deep Ensemble | 実装が簡単 | 計算コスト、過大/過小評価リスク | Phase 2 推奨 |
| Bayesian PINN | 原理的に整備 | 計算コスト高、事前分布選択が主観的 | 未検証 |
| EFI | 事前分布不要 | 新手法、実装例が少ない | 注目 |
| MC Dropout | 追加コスト少 | dropout 率選択が主観的 | 注意 |

### 3.5 MPC との連携

- MPC は run 内の高速な最適化を必要とするが、iPSC 培養の応答は遅い（時間〜日スケール）ため、**MPC の差別化価値は限定的**かもしれない〔推定〕。
- **auto_cell では、L1 ルールエンジンでカバーできる範囲が広く、MPC は「灌流率の制約付き最適化」など特定の用途に限定される**。
- Critical 制御経路は依然として決定的コア（L0/L1）に留め、DT はアドバイザリ/承認仲介に限定〔推定〕。

### 3.6 出典

| ID | タイトル | URL/DOI | 確度 |
|---|---|---|---|
| Thirugnanasambandam 2025 | A Physics-Informed Neural Network (PINN) framework for generic bioreactor modelling | DOI 10.1016/j.compchemeng.2025.109354 | 事実 |
| Yang 2024 | Hybrid Modeling of Fed-Batch Cell Culture Using PINN | DOI 10.1021/acs.iecr.4c01459 | 事実 |
| Catalão 2025 | Bioprocess MPC with PINN | DOI 10.1016/j.jprocont.2025.103594 | 事実 |
| Patel 2024 | MPC Using PINN (ADCHEM) | https://skoge.folk.ntnu.no/prost/proceedings/adchem-2024/files/0042.pdf | 事実 |
| Shih 2025 | UQ for PINN with EFI | arXiv 2505.19136 | 事実 |
| Nobar 2025 | Guided Multi-Fidelity BO with DT | arXiv 2509.17952 | 事実 |

---

## 4. Raman 校正戦略

### 4.1 現状と結論

- **in-line Raman は CHO/mAb 産業で TRL 8-9** だが、**iPSC 浮遊凝集体への実証は限定的**〔事実：Abu-Absi 2011; Costa 2024〕。レポートの楽観的評価をそのまま iPSC に転用できない。
- **iPSC 特異的な再校正が必須**〔推定〕。培地組成、代謝物濃度範囲、凝集体サイズ、細胞密度、シア感受性が CHO と大きく異なる（Manstein 2021; Kropp 2016）。
- **校正戦略は「Nova FLEX2 正解ラベル + capacitance VCD + Raman スペクトル + 凝集体画像」の三軸**〔提案〕。
- **凝集体と高密度細胞懸濁液による光散乱（Mie 散乱）が Raman 強度を減衰させ、PLS モデル精度を低下させる**〔事実：Yang 2024; Iversen 2014〕。

### 4.2 センサ役割分担

| センサ | 計測対象 | A 層での役割 | cadence | 信頼度 |
|---|---|---|---|---|
| in-line capacitance | VCD/biomass | 灌流/継代トリガの anchor | ~30 s | iPSC で定性的一致。細胞株毎再校正必要〔事実/推定〕 |
| in-line Raman | glucose, lactate, glutamine | 代謝物の in-line 推定、灌流/給餌トリガ | ~1 min | CHO で実証。iPSC では再校正必須〔推定〕 |
| at-line Nova FLEX2 | 16 項代謝物 + osmolality + viability + 細胞径 | Raman 校正の正解ラベル、BO 入力、リファレンス | ~4.5 min | 産業標準 at-line〔事実〕 |
| at-line 凝集体画像 | 凝集体径/形態 | 品質・継代判断の代理指標 | 日次〜条件起動 | v1 標準〔提案〕 |

### 4.3 PLS モデル構築

| 目的 | 推奨バッチ数 | 根拠 |
|---|---|---|
| 初期実証 | 3–5 バッチ | 推定；範囲内の濃度変動をカバー |
| ロバストモデル | 5–15 バッチ | 事実/推定：bioprocesstools.com; alignment メモ |
| スケール/クローン間転移 | 10 バッチ以上 | 推定：Yan 2024; Rowland-Jones 2021 |

性能目標：RMSEP ≤ 操作範囲の 10%、R² ≥ 0.95〔推定：ICH Q2 基準〕。

### 4.4 光散乱補正

| 戦略 | 詳細 | 出典 |
|---|---|---|
| SNV/MSC 前処理 | 乗法的散乱効果を正規化 | bioprocesstools.com |
| 内部標準（水ピーク 1600–1700 cm⁻¹） | 水ピーク強度で散乱減衰を補正 | Iversen 2014 |
| 細胞密度共変量 | VCD/capacitance を PLS モデルに追加 | 推定 |
| cell-scattering correction 式 | Log(R_cell) = a × C^b で減衰比をフィット | Yang 2024 |

### 4.5 v1/v2 採用ロードマップ

| 段階 | Raman の位置づけ | 条件 |
|---|---|---|
| v1（Phase 1） | **オプション観測**。Nova FLEX2 を正解とする校正計画を策定。Raman 値は記録・表示のみ。 | iPSC 校正データなしの段階 |
| v1.5（Phase 1 後期） | **アドバイザリ入力**。glucose/lactate 推定値を L1 イベントの追加参考情報として提示。制御アクションは人承認。 | 5 バッチ以上の校正・外部検証達成後 |
| v2（Phase 2） | **閉ループ入力候補**。校正モデルを `validate_tool_call` の包絡線と組み合わせて使用。 | 10 バッチ以上・光散乱補正・再現性確認後 |

### 4.6 出典

| ID | タイトル | URL/DOI | 確度 |
|---|---|---|---|
| Abu-Absi 2011 | Real time monitoring of multiple parameters in mammalian cell culture bioreactors using an in-line Raman spectroscopy probe | DOI 10.1002/bit.23023 | 事実 |
| Matthews 2016 | Closed loop control of lactate concentration by Raman spectroscopy | DOI 10.1002/bit.26018 | 事実 |
| Yang 2024 | In-line monitoring of bioreactor by Raman spectroscopy: cell-scattering correction | DOI 10.1016/j.jbiotec.2024.10.007 | 事実 |
| Costa 2024 | Harnessing Raman spectroscopy for cell therapy bioprocessing | DOI 10.1016/j.biotechadv.2024.108166 | 事実 |
| Machleidt 2024 | Cross-clone Raman calibration models in CHO | DOI 10.1002/biot.202300289 | 事実 |
| Pétillot 2020 | Calibration transfer for bioprocess Raman monitoring | DOI 10.1002/eng2.12230 | 事実 |

---

## 5. CHO → iPSC CPP 転換

### 5.1 代謝プロファイルの相違

| 特性 | CHO 典型値/傾向 | iPSC 典型値/傾向 | 転用可否 |
|---|---|---|---|
| グルコース消費 | 高い；最低 2–3 g/L（11–17 mM）維持推奨 | K_Glc=1.5 mM（Manstein モデル） | 不可 |
| 乳酸産生 | 急速な乳酸蓄積 | K_Lac=50 mM（Manstein モデル） | 不可 |
| アンモニア阻害 | 5.1 mM で成長阻害、8 mM で 50% 成長低下 | **未確定** | 不可 |
| 浸透圧許容 | 最適 280–320、380–450 超で成長低下 | K_Osm=500 mOsm/kg（Manstein モデル） | 不可 |
| 目的関数 | mAb タイトル、糖鎖パターン | 収量 × 生存率 × 多能性マーカー × 凝集体サイズ | 不可 |

〔事実：Manstein 2021; Xing 2008; Mabion 2025; GFI 2025〕

### 5.2 凝集体形成が CPP に与える影響

- iPSC 浮遊培養では凝集体径が酸素/栄養拡散、シアストレス、品質（未分化性）を同時に規定。CHO の単一懸濁とは異なる〔事実：Borys 2021; Huang 2020〕。
- 凝集体内酸素拡散限界は血管からの距離 100–200 µm と参照され、収穫日平均径を 300 µm 以下に制御する攪拌スキームが開発された〔事実：Huang 2020〕。
- Borys et al. 2021 は Vertical-Wheel で 40 rpm が最大増殖を示し、day 5 の凝集体径が 169–275 µm、**>400 µm で壊死が予想される**と報告した〔事実：DOI 10.1186/s13287-020-02109-4〕。
- auto_cell A 層では `cpp_aggregate_diameter`（150–350 µm）が CPP として定義されているが、平均径だけでなく大径凝集体割合（>400 µm）も考慮すべき〔推定〕。

### 5.3 目的関数の違い

- CHO の目的関数：抗体タイトル（g/L）、収率（viable cell density × specific productivity）、糖鎖パターン（CQA）、培地コスト/プロセス時間。
- iPSC の目的関数：細胞収量 × 生存率 × 未分化マーカー陽性率（OCT4/SOX2/NANOG/SSEA/TRA）× 凝集体適正サイズ比率。重みは細胞株・最終用途（分化先）で変動〔推定〕。
- Seo et al. 2021 は OCT4 と SOX2/NANOG が異なる添加物によって制御され、**単一目的関数では最適化困難**であることを示唆した〔事実/推定〕。

### 5.4 転用禁止リスト（棄却）

| 項目 | CHO 値/傾向 | iPSC での扱い |
|---|---|---|
| 乳酸閾値 | 15–50 mM（株依存） | Manstein モデル値を初期値とし実株で再校正 |
| アンモニア閾値 | 5 mM で成長阻害 | **未確定**；監視のみ |
| 浸透圧上限 | 380–450 mOsm/kg | K_Osm=500 mOsm/kg（モデル値）で再校正 |
| グルコース下限 | 2–3 g/L 維持 | K_Glc=1.5 mM（モデル値） |
| 攪拌最適 rpm | 80–120 rpm（インペラ槽） | 40–60 rpm（Vertical-Wheel）、80 rpm（DASbox 150mL） |
| 灌流率 | CHO perfusion 0.029–0.075 L/h（5L） | 0→7 vvd（Manstein） |
| 目的関数 | mAb タイトル | 収量×生存率×多能性マーカー |
| 低乳酸株育成（PYC2 等） | 代謝改変 | iPSC 治療用製品では遺伝子改変不可 |
| 高比重・長期培養 | CHO の標準戦略 | iPSC では凝集体サイズ制限・多能性喪失・核型異常リスク |

### 5.5 出典

| ID | タイトル | URL/DOI | 確度 |
|---|---|---|---|
| Manstein 2021 | High density bioprocessing of hPSCs | DOI 10.1002/sctm.20-0453 | 事実 |
| Borys 2021 | Overcoming bioprocess bottlenecks in large-scale expansion of hiPSC aggregates | DOI 10.1186/s13287-020-02109-4 | 事実 |
| Huang 2020 | Process development and scale-up of PSC manufacturing | https://www.insights.bio/.../1784/ | 事実 |
| Xing 2008 | Identifying inhibitory threshold values in CHO cell culture | DOI 10.1021/bp070466m | 事実（CHO） |
| Seo 2021 | Addressing bioreactor hiPSC aggregate stability using DoE | bioreactor_iPSC_aggregate_stability_publication.pdf | 事実/推定 |

---

## 6. PIC/S Annex 22 ロードマップ

### 6.1 Annex 22 の概要

- **正式名称**: EudraLex Volume 4 — GMP Annex 22: Artificial Intelligence（草案）〔事実：EC/PIC/S 2025-07-07〕。
- **公開協議**: 2025-07-07 〜 2025-10-07〔事実〕。
- **最終化・施行**: 2026 年最終採用、2027–2028 年段階的施行が業界レポートで予想される〔推定：industry analysis〕。ただし公式な施行日は未発表。
- **上位文書**: Annex 11（Computerised Systems）、Chapter 4 と併用。Annex 22 は AI/ML 特有の追加要求を定める〔事実〕。

### 6.2 主要要求事項

Annex 22 1.Scope によれば、クリティカル用途では以下のみ許容される。

| 許容 | 禁止（クリティカル用途） |
|---|---|
| 静的モデル（static model） | 動的モデル（dynamic model） |
| 決定論的出力（deterministic output） | 確率的モデル（probabilistic model） |
| 明示的ルール・状態機械 | 生成 AI / LLM |

生成 AI/LLM は**非クリティカル用途**であれば、適切な資格・訓練を受けた人間による HITL 確認のもと使用可能〔事実〕。

### 6.3 L0–L3 制御層と Annex 22 の対応

| 層 | 構成要素 | Annex 22 分類 | 技術的統制 |
|---|---|---|---|
| L0 | 局所 PID | AI ではない決定論的制御器 | ベンダ IQ/OQ |
| L1 | レシピ DSL/状態機械/ルールエンジン | 明示的ルールによるクリティカル制御 | `validate_tool_call`、包絡線、監査ログ |
| L2 | Ax/BoTorch バッチ BO + GP | 静的モデルとして扱う（訓練データ固定・シード固定） | データ分離、モデルカード、獲得関数説明、信頼度 |
| L3 | 薄い LLM オーケストレータ | **非クリティカルのみ**、HITL | プロンプトバージョニング、入出力ログ、人承認 |

A 層 v1 では、クリティカル制御経路に AI/ML を導入しないため、Annex 22 の厳格な AI 検証要件は将来の Raman PLS や画像 DL 等に限定される〔推定〕。

### 6.4 R&D 一次で導入する 5 本柱

1. **ALCOA-lite + 監査ログ**: 全副作用ツール呼び出しを「誰・いつ・何を・なぜ」で構造化ログ化。〔事実：integrated_report §6.2〕
2. **意図用途（Intended Use）文書化**: L2 BO/GP、将来の Raman PLS/画像 DL 向けテンプレート作成。
3. **データ分離と職員独立性**: train/valid/test のリポジトリ分離、 dual control/4-eyes で緩和。
4. **XAI と信頼度スコア**: GP 事後分散、PLS 予測信頼区間、SHAP/Grad-CAM 等。
5. **Human-on-the-loop（HITL）**: 包絡線外アクション、BO 提案、継代トリガの承認を運用開始。

### 6.5 GAMP5 AI Guide との関係

- **GAMP5 2nd Ed Appendix D11**: AI/ML ライフサイクル（concept / project / operation）を導入〔事実：ISPE GAMP5〕。
- **GAMP AI Guide（2025）**: データガバナンス、モデルガバナンス、動的システム、リスク管理を包括的に扱う〔事実〕。
- L2 BO/GP → GAMP Category 4/5、L3 LLM → Category 5 + 非クリティカル用途限定、データパイプライン → Category 1/3〔推定〕。

### 6.6 出典

| ID | タイトル | URL/DOI | 確度 |
|---|---|---|---|
| src_pics_annex22_draft | EudraLex Volume 4 — Draft Annex 22: AI (July 2025) | https://health.ec.europa.eu/.../annex22_consultation_guideline_en.pdf | 事実 |
| src_eu_ai_act | Regulation (EU) 2024/1689 — AI Act | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689 | 事実 |
| src_gamp5_ai | ISPE GAMP Guide: Artificial Intelligence (2025) | https://ispe.org/publications/guidance-documents/gamp-guide-artificial-intelligence | 事実 |

---

## 7. 浮遊凝集体画像解析

### 7.1 現状と結論

- **凝集体径は v1 で at-line 画像が現実的**: in-line DHM/FBRM は技術的に存在するが、iPSC 凝集体の turn-key 実証・校正は限定的。v1 では at-line 明視野/位相差画像（FlowCam/Kropp 型バイパス顕微鏡または手動サンプリング＋顕微鏡）を主軸とする〔事実：Borys 2021; Eppendorf AN485; StemCell mTeSR 3D〕。
- **凝集体径と品質は相関するが単純なしきい値ではない**: 径 150–350 µm（Manstein/Borys 設計値）を超えると拡散制限による未分化性低下・壊死リスクが増大するが、細胞株・培地・撹拌による相互作用が大きい〔事実/推定〕。
- **label-free DL による品質代理指標は有望だが未確定**: 2D コロニー・organoid の明視野/位相差から分化状態を予測する研究は多数あるが、**iPSC 浮遊凝集体**に特化した実証は乏しく、OCT4/SOX2/NANOG 等との定量的対応は未確定〔推定：Chu 2023; Park 2022; Piotrowski 2021〕。
- **2D confluency は浮遊凝集体に不適用**〔事実〕。

### 7.2 技術比較

| 技術 | 配置 | iPSC 実証 | v1 位置づけ |
|---|---|---|---|
| DHM / Ovizio iLINE-F PRO | in-line | 懸浮細胞・MSC・CAR-T で実証。iPSC 凝集体 turn-key は限定的 | オプション〜後段 |
| FBRM / ParticleTrack | in-line | 結晶化・凝集プロセスで広く使用。iPSC 直接適用例は少ない | トレンド監視（画像法で補正） |
| FlowCam | at-line / offline | 海洋微生物・粒子解析で実績。iPSC 凝集体報告は少ない | 日次 at-line |
| 明視野/位相差 at-line | at-line | **iPSC 浮遊凝集体で最も一般的** | **v1 必須** |

### 7.3 凝集体品質代理指標

画像特徴量から OCT4/SOX2/NANOG/SSEA4/TRA-1-60 等の offline 品質マーカーを推定する代理指標〔推定〕：

- サイズ：面積、等価直径、最大/最小径
- 形状：円形度、アスペクト比、輪郭の粗さ
- 内部構造：位相差画像での内部輝度勾配
- 分布：サイズ分布のピーク数
- 質感：細胞密度・パッキングの均一性

これらを BO 目的関数の品質項として使う場合、まず offline 正解ラベルとの回帰/分類モデル構築が必要〔推定〕。

### 7.4 Human-on-the-loop

- 包絡線内は自律。
- 径の急増、二峰分布、DL 品質代理指標の低信頼度予測時は `trigger_passage` または `set_agitation_rpm` の変更を承認要求へエスカレーション。
- モデルの予測不確実性（エントロピー、MC dropout 分散、OOD 検出）を可視化し、閾値超過時は人の判断を仰ぐ〔推定〕。

### 7.5 出典

| ID | タイトル | URL/DOI | 確度 |
|---|---|---|---|
| Borys 2021 | Overcoming bioprocess bottlenecks in large-scale expansion of hiPSC aggregates | DOI 10.1186/s13287-020-02109-4 | 事実 |
| Eppendorf AN485 | hiPSC Aggregate Expansion in Stirred-tank Bioreactors | https://www.eppendorf.com/.../AN_485.pdf | 事実 |
| Kropp 2019 | at-line bypass imaging of hiPSC aggregates | DOI 10.1038/s41598-019-48814-w | 事実 |
| Chu 2023 | hiPSC reprogramming DL prediction | DOI 10.1016/j.cmpb.2022.107264 | 事実 |
| Park 2022 | Deep learning predicts kidney organoid differentiation | 10.23876/j.krcp.22.017 | 事実 |

---

## 8. 統合ロードマップ（v1/Phase2/Phase3）

### 8.1 v1 必須（0–12 ヶ月）

| 領域 | 採用内容 | 棄却/後回し |
|---|---|---|
| 制御コア | L1 決定的レシピ/ルールエンジン、状態機械 | MPC、PINN/DT、LLM による Critical 制御 |
| プロセスモデル | Manstein ODE `plant_model`（決定的検証リグ） | Hybrid ODE+NN、PINN |
| 代謝物モニタリング | at-line Nova FLEX2（正解ラベル）、capacitance VCD | Raman 閉ループ制御 |
| 凝集体モニタリング | at-line 明視野/位相差画像（必須）、ImageJ/自動解析 | DHM/FBRM/FlowCam はオプション〜後段 |
| AI/ML | L2 BO/GP（静的モデルとして扱う）、L3 LLM は非クリティカルのみ | Critical 用途での AI/ML |
| 技術的統制 | ALCOA-lite 監査ログ、意図用途文書テンプレート、データ分離設計、HITL 承認ワークフロー | 完全電子署名・職員独立性（GMP 移行時） |

### 8.2 Phase 2（12–24 ヶ月）

| 領域 | 採用内容 | 前提条件 |
|---|---|---|
| MPC | plant_model ベース MPC シミュレーション。perfusion rate 単一 MV。目的関数 = VCD 軌道追従 + 乳酸抑制 + 培地コスト。 | 30+ run 蓄積、Nova/Raman 校正完了 |
| PINN/DT | GP バイアス補正、ベイズパラメータ同定。Hybrid ODE+NN の PoC。 | 30+ run 蓄積 |
| Raman | PLS モデルによる glucose/lactate 推定を **アドバイザリ入力**として提示。低信頼度時は Nova 優先。 | 5+ バッチ校正・外部検証達成 |
| 画像解析 | 凝集体径・形態メトリクス（面積、円形度、分布）を BO 入力へ。 | offline 正解ラベル取得開始 |
| Annex 22 | Raman PLS 等の静的決定論的モデル導入。チェックサム・バージョン固定・再現性テスト。信頼度スコア・XAI・ドリフト監視。 | 校正データ蓄積 |

### 8.3 Phase 3（24–48 ヶ月）

| 領域 | 採用内容 | 前提条件 |
|---|---|---|
| MPC | perfusion rate + glucose/glutamine bolus feed + agitation setpoint の多変数 MPC。適応更新、経済 MPC。 | 50–100 run 蓄積、構造モデル検証 |
| PINN/DT | Hybrid ODE+NN を L2 BO の低忠実度モデルとして本格運用。PINN/DT + MPC のアドバイザリ機能検討。 | 50–100 run 蓄積 |
| Raman | **閉ループ入力候補**。校正モデルを `validate_tool_call` の包絡線と組み合わせて灌流/給餌トリガに使用。 | 10+ バッチ・光散乱補正・再現性確認 |
| 画像解析 | DL 品質代理指標を BO 目的関数項に統合。 | 数十〜数百バッチの offline 正解ラベル |
| GMP 移行 | L2 AI コンポーネント・データパイプラインの IQ/OQ/PQ。性能等価性実証。完全な職員独立性。 | プログラム全体の QMS/CSV/規制チーム |

### 8.4 調査継続

| # | 項目 | 対象領域 |
|---|---|---|
| 1 | iPSC 凝集体特有の動的モデル（凝集体形成・シア応答） | MPC/PINN |
| 2 | Raman ベース in-line glucose/lactate の iPSC 校正精度 | Raman |
| 3 | MPC 目的関数の重み（収量 vs 品質 vs コスト） | MPC/BO |
| 4 | 求解時間と cadence（分単位 vs 時間単位） | MPC |
| 5 | Annex 22 下での MPC 検証戦略 | Annex 22/MPC |
| 6 | 細胞保持デバイス（ATF/TFF/重力沈降）の動態とシア | MPC |
| 7 | iPSC 浮遊凝集体固有の PINN 構造 | PINN/DT |
| 8 | データ効率性（50–100 バッチは CHO 基準） | PINN/DT |
| 9 | 外挿性能・ドメイン適応 | PINN/DT/Raman/画像 |
| 10 | 不確実性定量化の校正（95% CI カバレッジ） | PINN/DT |
| 11 | 品質指標の予測（OCT4/SOX2 等 offline ラベル） | PINN/DT/画像 |
| 12 | アンモニアの iPSC ネイティブ閾値 | CHO→iPSC CPP |
| 13 | 凝集体径分布（歪度/大径割合）の品質相関 | 画像/CPP |
| 14 | シアストレスの定量指標（Kolmogorov 長等） | CPP/MPC |
| 15 | 画像技術の iPSC 校正曲線 | 画像 |
| 16 | 2D 画像解析モデルの凝集体転移効率 | 画像 |
| 17 | DL 品質指標の BO 目的関数重み | 画像/BO |
| 18 | Annex 22 最終文本・施行日 | Annex 22 |
| 19 | BO/GP を「静的決定論的モデル」と見なせるか | Annex 22/BO |
| 20 | 低信頼度閾値のプロセス毎検証 | 全 AI/ML |

### 8.5 棄却リスト

| # | 項目 | 理由 |
|---|---|---|
| 1 | CHO 由来の乳酸/アンモニア/浸透圧/グルコース閾値を iPSC に直接適用 | 細胞種・培地・密度依存 |
| 2 | CHO の mAb タイトル目的関数を iPSC に適用 | 製品が細胞そのもので品質指標が異なる |
| 3 | CHO の高比重・長期培養戦略を iPSC に適用 | 凝集体サイズ制限・多能性喪失・核型異常リスク |
| 4 | CHO の抗体特化 feed 設計を iPSC に適用 | 成長因子・ROCK 阻害剤・凝集体安定化が重要 |
| 5 | 2D confluency を浮遊凝集体の指標として使用 | 浮遊凝集体には培養面が存在しない |
| 6 | 生成 AI/LLM を Critical 制御経路に使用 | PIC/S Annex 22 で禁止 |
| 7 | 動的/確率的 AI モデルを Critical GMP 用途に使用 | PIC/S Annex 22 で禁止 |
| 8 | Raman CHO モデルを iPSC に転用 | マトリックス・光散乱・代謝プロファイルが異なる |
| 9 | MPC の CHO 実績（タイトル 2% 向上等）を iPSC KPI に転用 | iPSC 目的関数は未分化性・凝集体品質 |
| 10 | PINN/DT の CHO 産業例を iPSC にそのまま適用 | 凝集体形成・品質指標が未カバー |

---

## 9. 未解決事項

本統合レポートが特定した未解決事項を、優先度と担当領域別に集約する。

### 9.1 v1 実装前に解決すべき事項

| # | 項目 | 影響 | 次ステップ | 確度 |
|---|---|---|---|---|
| U1 | Manstein ODE の細胞株・培地再校正 | L1 CPP 閾値の妥当性 | 最初の数 run でパラメータフィット | 推定 |
| U2 | `cpp_aggregate_diameter` の初期値 150–350 µm の細胞株依存性 | L1 イベント信頼性 | 複数株で分布と品質相関調査 | 未確定 |
| U3 | アンモニアの iPSC ネイティブ閾値 | L1 イベント化の可否 | 文献サーチ or 実験決定 | 未確定 |
| U4 | BO 目的関数の重み（収量 vs 多能性 vs コスト） | L2 最適化方向性 | 研究者ヒアリング | 推定 |
| U5 | 低信頼度閾値の初期値 | HITL 過剰/過少エスカレーション | 感度分析 | 未確定 |

### 9.2 Phase 2 移行条件として解決すべき事項

| # | 項目 | 影響 | 次ステップ | 確度 |
|---|---|---|---|---|
| U6 | Raman PLS の iPSC 校正精度（RMSEP、R²） | Raman アドバイザリ入力の信頼性 | 5+ バッチ校正実験 | 未確定 |
| U7 | 凝集体・高密度細胞による Raman 光散乱補正の定量式 | Raman 推定精度 | 標準添加/混合標準実験 | 推定 |
| U8 | MPC シミュレータの求解時間と cadence | MPC 実用性 | do-mpc/acados プロトタイプ | 未確定 |
| U9 | GP バイアス補正の表現力（30 run 程度） | L2 BO 精度 | 実データ検証 | 推定 |
| U10 | 凝集体画像の自動セグメンテーション精度 | 画像定量化 | U-Net/Mask R-CNN 転移学習 | 推定 |

### 9.3 Phase 3 移行条件として解決すべき事項

| # | 項目 | 影響 | 次ステップ | 確度 |
|---|---|---|---|---|
| U11 | iPSC 凝集体固有の Hybrid ODE+NN/PINN 構造 | DT 信頼性 | 小規模実データで構造比較 | 未確定 |
| U12 | 多変数 MPC の適応更新アルゴリズム | 細胞株変動対応 | DARX/適応 MHE 実装 | 推定 |
| U13 | DL 品質代理指標と OCT4/SOX2/NANOG の定量的対応 | BO 品質項の信頼性 | 数十〜数百バッチの offline 正解ラベル | 未確定 |
| U14 | 経済 MPC の目的関数重みと Pareto 最適化 | 収量×品質×コスト | 研究者ヒアリング＋感度分析 | 推定 |
| U15 | Annex 22 下での AI/ML 検証戦略 | GMP 移行性 | GAMP5 Cat.4/5 文書化計画 | 推定 |

### 9.4 長期的・外部依存事項

| # | 項目 | 影響 | 次ステップ | 確度 |
|---|---|---|---|---|
| U16 | Annex 22 最終文本・施行日 | GMP 移行計画 | 規制動向モニタリング | 未確定 |
| U17 | 規制当局が BO/GP を「静的決定論的モデル」と見なす解釈 | L2 BO の Annex 22 分類 | QRM/規制コンサル | 未確定 |
| U18 | ベンダー（Raman、DHM、FBRM）の iPSC 凝集体向け検証データ | 機器選定・校正 | ベンダー PoC/協業 | 未確定 |

---

## 10. トレーサビリティ

### 10.1 入力ファイル（Mode A）

| ドメイン | ファイルパス |
|---|---|
| MPC | `docs/design/ground_knowledge/additional_mpc_for_ipsc.md` |
| PINN/DT | `docs/design/ground_knowledge/additional_pinn_dt_for_ipsc.md` |
| Raman | `docs/design/ground_knowledge/additional_raman_calibration_ipsc.md` |
| CHO→iPSC CPP | `docs/design/ground_knowledge/additional_cho_to_ipsc_cpp.md` |
| Annex 22 | `docs/design/ground_knowledge/additional_annex22_roadmap.md` |
| Aggregate Imaging | `docs/design/ground_knowledge/additional_aggregate_imaging.md` |

### 10.2 入力ファイル（Mode B）

| ドメイン | ファイルパス |
|---|---|
| MPC | `docs/knowledge_graph/generated/additional_mpc_kg_diff.json` |
| PINN/DT | `docs/knowledge_graph/generated/additional_pinn_dt_kg_diff.json` |
| Raman | `docs/knowledge_graph/generated/additional_raman_kg_diff.json` |
| CHO→iPSC CPP | `docs/knowledge_graph/generated/additional_cho_ipsc_kg_diff.json` |
| Annex 22 | `docs/knowledge_graph/generated/additional_annex22_kg_diff.json` |
| Aggregate Imaging | `docs/knowledge_graph/generated/additional_aggregate_imaging_kg_diff.json` |

### 10.3 出力ファイル

| ファイル | パス |
|---|---|
| 統合調査レポート | `docs/design/ground_knowledge/additional_investigation_integrated.md` |
| 統合 KG 差分 JSON | `docs/knowledge_graph/generated/additional_investigation_diff.json` |

### 10.4 統合 KG 差分の検証結果

- **ベース KG**: `docs/knowledge_graph/knowledge_graph_v2.json`（nodes=197, edges=401）
- **統合差分**: nodes=143, edges=291, sources=56
- **重複検出**: `src_yang_2024` が PINN/DT 差分と Raman 差分で出現。内容は別論文のため、`src_yang_2024_pinn` / `src_yang_2024_raman` にリネームして解消。
- **v2 との衝突**: ノード ID 衝突なし、エッジ triple 重複なし。
- **エッジ検証**: 全エッジの source/target が `knowledge_graph_v2.json` または統合差分ノードに存在。

### 10.5 主な前提文書

| ID | タイトル | パス |
|---|---|---|
| ADR-0001 | Control architecture — thin LLM orchestrator over deterministic tools + Bayesian optimization | `docs/design/adr/0001-control-architecture.md` |
| requirements | auto_cell A 層要求仕様 | `docs/design/requirements.md` |
| kg_bridge | KG → auto_cell 設計ブリッジ | `docs/design/kg_to_auto_cell.md` |
| integrated_report | auto_cell A 層統合設計根拠レポート | `docs/design/ground_knowledge/integrated_report.md` |
| alignment | ダウンロードレポートと auto_cell 設計方向性の照合分析 | `docs/design/alignment_with_downloaded_report.md` |

---

*本レポートは A 層（iPSC 浮遊/凝集体バイオリアクター制御）に限定。CHO/mAb 由来の数値を iPSC にそのまま転用しないことを原則とし、全主張に出典と確度（事実/推定/未確定/設計判断）を付与した。*
