# 追加調査: iPSC 浮遊灌流における MPC の適用

> **担当**: MPC for iPSC perfusion/suspension Agent  
> **Scope**: auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御、Manstein 型灌流 0→7 vvd）  
> **Date**: 2026-06-16  
> **前提**: ADR-0001（L0 局所 PID + L1 決定的レシピ/ルール + L2 BO + L3 薄い LLM）、R&D 一次・Human-on-the-loop

## 1. Executive Summary

本調査は、`/home/sin/Downloads/report/report.md`（フィジカルAI包括調査レポート）と auto_cell A 層設計の照合分析で顕在化した **「MPC の将来位置づけ」** ギャップを補完する。結論から述べると、**iPSC 浮遊灌流プロセスへの MPC 導入は技術的に有望だが、現時点では実証例が限定的であり、A 層 v1 の L1 決定的レシピ/ルールを置き換えるのではなく、段階的に拡張する形が妥当** である。

主要結論:

1. **iPSC 浮遊灌流そのものの MPC 実証例は少ない**〔事実〕。哺乳類細胞培養の MPC 実績は主に CHO fed-batch/perfusion 由来で、iPSC 凝集体への直接転用にはモデル・制約・目的関数の再検討が必要。
2. **灌流率を主操作変数とする多変数制約最適化は原理的に可能**〔推定〕。状態 = VCD/glucose/lactate/glutamine/osmolality/aggregate diameter、操作変数 = perfusion rate（±bolus feed）、制約 = CPP 包絡線・ポンプレート・凝集体シア・培地コスト、という枠組みで定式化できる。
3. **MPC は L1 ルールエンジンの「未来の拡張」に位置づける**〔推定〕。v1 は決定的レシピ/ルールで十分。MPC は Phase 2（12–24 ヶ月）以降、特に動的灌流戦略・代謝フィードバック・経済性最適化で差別化する。
4. **Human-on-the-loop・GMP-ready 設計を前提にする**〔事実/推定〕。Annex 22 は Critical 制御経路で決定論的モデルを要求。MPC は静的・決定論的モデル（線形/非線形 ODE + 制約）として文書化すれば対応可能。
5. **CHO 由来の数値（抗体タイトル 2% 向上、グルコース 35% 増加等）は iPSC にそのまま転用しない**〔設計判断〕。

---

## 2. 調査観点と回答

### 2.1 iPSC 浮遊灌流プロセスにおける MPC の適用例

#### 2.1.1 直接的な iPSC MPC 実証は限定的

- iPSC 浮遊凝集体培養への MPC 適用を直接的に報告した査読付き論文は、本調査で確認された範囲では **存在しない**〔未確定/事実：Web 検索・文献サーベイで該当論文を発見できず〕。
- 最も近い領域は、**MSC・造血幹細胞・汎用細胞治療培養における乳酸ベース MPC** である。Van Beylen et al. (2020) は、人骨髄由来間葉系幹細胞（hBM-MSC）の 2D/マルチプレート培養で、累積乳酸濃度を成長代理指標とし、培地交換量を入力とする適応 DARX-MPC を提案した。3 ドナー×6 戦略×3 反復で検証し、DARX モデルは同実験データ上で R² 99.80% ± 0.02%、未知トリプリケートへの転用でも平均 96.57% の適合を示した〔DOI 10.3390/bioengineering7030078〕。
- **この例は iPSC ではないが、「乳酸を soft sensor とする適応 MPC」というアイデアは iPSC 浮遊灌流でも転用可能** 〔推定〕。

#### 2.1.2 近縁：PSC 灌流の動的/閉ループ戦略

- **Huang et al. 2020** は、ESI-017 hESC および NCRM1 iPSC の 250 mL DASbox → 1 L BioFlo 320 → 10 L XDR-10 撹拌槽スケールアップで、**pH 6.8 到達をトリガーとする動的灌流戦略**を実証した。Perfusion rate を 50% vvd から 30% 増加/日で ramp させる戦略により、固定灌流と比較して day 6 で平均 25% の高密度化、乳酸を 15 mM 未満に抑制した〔DOI 10.18063/cgti.v1.i1.1784 / insights.bio〕。
- この動的戦略は「ルールベース」だが、**MPC に置き換えることで、トリガー条件を多変数（glucose/lactate/osmolality/VCD）に拡張し、ramp 率を制約付き最適化できる** 〔推定〕。
- **Manstein & Zweigerdt 2021** は、DASbox 150 mL hiPSC 灌流で 7 日で 35×10⁶ cells/mL（70 倍拡大）を達成。Berkeley-Madonna を用いた in silico モデルでパラメータ最適化を実施。最適化された戦略は灌流率 1→2 vvd、グルコース濃度 3.15→7.65 g/L、80 rpm 撹拌等であった〔DOI 10.1002/sctm.20-0453; PMID 33660952; PMC8666714〕。これは **run 間 BO 最適化の文脈**であり、run 内 MPC ではないが、 plant_model（Manstein ODE）が MPC の内部モデル候補となる。

#### 2.1.3 CHO/mAb 由来の MPC 実績（参考・転用注意）

- **Rashedi et al. (DYCOPS-2022)** は Amgen の fed-batch CHO プロセスで線形 MPC（LMPC）を実機適用。VCD・TCD・viability・GLC・LAC・GLN・GLU・NH4・Na・K・osmolality を状態、feed を入力、30 日予測ホライズン・8 日制御ホライズンで、最終タイトル 2% 向上、グルコース投与量 35% 増加、タンパク質純度（CEX-HPLC main peak）も改善した〔DYCOPS-2022 paper 0202; https://skoge.folk.ntnu.no/prost/proceedings/dycops-2022/files/0202.pdf〕。
- レポート `/home/sin/Downloads/report/report.md` でも同様に CHO fed-batch MPC（抗体タイトル 2% 向上、グルコース投与 35% 増加）を引用している〔MDPI 1422-0067/27/5/2388〕。
- **これらの数値は iPSC 製品（未分化マーカー維持・凝集体品質）には直接当てはまらない** 〔事実〕。

#### 2.1.4 制御層としての位置づけ

- レポートは MPC を「制御層（Control Layer）」に配置し、MPC/BO/PINN を「XAI 対応の決定論的下位制御器」として Annex 22 に対応させるハイブリッドアーキテクチャを提案している。
- auto_cell A 層では、ADR-0001 で **L1 = 決定的レシピ/ルール、L2 = BO（run 間）** と決定済み。MPC は **L1 の拡張路線図**に追加するのが整合性を保つ。

### 2.2 灌流率を操作変数とする多変数制約最適化の可否

#### 2.2.1 状態・操作変数・制約の定式化案

A 層 iPSC 浮遊灌流（Manstein 型）では、以下の定式化が可能である〔推定〕：

| 要素 | 候補 | 備考 |
|---|---|---|
| **状態 x** | VCD, viability, glucose, lactate, glutamine, osmolality, aggregate diameter, DO, pH | glucose/lactate は in-line Raman または at-line Nova；VCD は capacitance；凝集体径は at-line 画像 |
| **操作変数 u** | Perfusion rate (vvd), 必要に応じ glucose/glutamine bolus feed | 主レバーは灌流率（§7.2） |
| **外乱 w** | 細胞株特異的成長率、凝集体形成動態、温度ラボジット | 適応更新で吸収 |
| **制約 g(x,u)** | 0 ≤ perfusion ≤ 7 vvd; glucose > 1.5 mM; lactate < 50 mM; osmolality < 500 mOsm/kg; aggregate 150–350 µm; pump rate ramp ≤ 0.5 vvd/30 min | CPP 包絡線（Manstein 2021） |
| **目的関数 J** | VCD 到達・生存率・未分化マーカー維持・培地コスト・乳酸抑制の多目的/重み付き | 品質項は offline/run 単位で検証 |

#### 2.2.2 多変数制約最適化の技術的妥当性

- 灌流培養は本質的に **MIMO システム** である。PSE Community のレビューでは、「perfusion cultures are MIMO systems which can be controlled via dilution and perfusion rates」と指摘されているが、産業実装は SISO 中心で、理論と実践のギャップが大きい〔LAPSE-2020.0565-1v1〕。
- シミュレーション研究では、feed/perfusion/bleed ストリームを同時操作して biomass・代謝物濃度を制御する多変数非線形予測制御が報告されているが、iPSC 凝集体特有のモデルは未整備〔LAPSE-2020.0565-1v1〕。
- **結論：多変数制約最適化は原理的に可能だが、iPSC 凝集体用の信頼できる動的モデル・シア制約・細胞保持デバイスモデルが前提** 〔推定〕。

#### 2.2.3 灌流率制御の戦略比較

| 戦略 | 操作変数 | フィードバック | 文献的根拠 |
|---|---|---|---|
| 固定灌流 | time-based perfusion rate | なし | Huang 2020 baseline（50% vvd） |
| ルールベース動的灌流 | pH トリガー + 30% ramp | pH / daily metabolite | Huang 2020（25% 向上） |
| CSPR 制御 | perfusion rate = q × VCD | online biomass / offline VCD | Konstantinov et al. 2006; Wolf 2018 thesis |
| 代謝物制御 | perfusion rate by glucose/lactate setpoint | Raman / at-line analyzer | Dowd et al. 2001; Meuwly et al. 2006 |
| **MPC** | perfusion rate (+ feed bolus) | 多変数状態 + 予測モデル | Rashedi 2022; Van Beylen 2020（参考） |

### 2.3 MPC とルールエンジンの比較

| 観点 | L1 決定的レシピ/ルールエンジン（v1） | MPC（将来拡張） |
|---|---|---|
| **制御哲学** | 状態→アクションの離散ルール + CPP 包絡線 | 動的モデル + 制約付き滚动最適化 |
| **モデル必要度** | 低（閾値・状態機械） | 高（ODE/データ駆動/ハイブリッド） |
| **最適性** | 局所的・ヒューリスティック | 多変数・長期報酬を考慮 |
| **柔軟性** | 新イベントはルール追加が必要 | 目的関数・制約変更で対応 |
| **実装コスト** | 低（YAML/JSON DSL + 状態機械） | 高（モデル同定・求解器・検証） |
| **検証性** | 高（決定的・テスト容易） | 中～高（モデル・ソルバー・制約を文書化） |
| **Annex 22 対応** | 容易（静的・決定論的） | 可能（モデルが静的・決定論的であれば） |
| **Human-on-the-loop** | 包絡線外で承認 | 提案軌道・制約逸脱リスクで承認 |
| **遅延許容** | 30 s+ / イベント | 分～時間オーダー（iPSC は遅い動態） |
| **失敗モード** | ルール未該当 → ホールド/人へ | モデルミスマッチ → 制約違反/不適切な feed → ホールド |

**比較結論**: v1 ではルールエンジンを採用し、MPC は **Phase 2 以降の拡張** とする。MPC の導入は、まず plant_model（Manstein ODE）を内部モデルとしたシミュレーション評価から始め、実データでモデル適応後に閉ループ昇格させる〔推定〕。

### 2.4 auto_cell L1 への導入フェーズ（将来拡張路線図）

#### Phase 1（0–12 ヶ月）— v1: ルールベース L1

- **MPC は導入しない**。
- L1 は決定的レシピ/ルールで、灌流率を glucose/lactate/osmolality トリガーで条件起動（0→7 vvd）。
- plant_model（Manstein ODE）を Tier2 検証リグとして整備し、将来 MPC の内部モデル候補とする。
- Human-on-the-loop：包絡線外 set_perfusion_rate・trigger_passage・BO 提案は人承認。

#### Phase 2（12–24 ヶ月）— MPC フィージビリティ・シミュレーション

- **MPC シミュレータの構築**：`sim/plant_model`（Manstein ODE）または線形化データ駆動モデルを用いた NMPC/LMPC。
- **単一操作変数から開始**：perfusion rate のみを最適化。目的関数 = VCD 軌道追従 + 乳酸抑制 + 培地コスト。
- **制約**：CPP 包絡線、pump ramp rate、凝集体径（間接的に shear 制約）。
- **Human-on-the-loop**：MPC 提案軌道を HMI で提示、研究者が承認/調整後に L1 へ反映。
- **ライブラリ選定**：CasADi + do-mpc（研究・プロトタイプ）または acados（高速組み込み）。

#### Phase 3（24–48 ヶ月）— 多変数 MPC 実機適用

- **多操作変数**：perfusion rate + glucose/glutamine bolus feed + agitation setpoint（必要に応じ）。
- **適応更新**：Raman / Nova / capacitance からのオンライン・at-line データでモデルパラメータを逐次更新（Van Beylen 2020 の DARX 適応アプローチを参考）。
- **経済 MPC（Economic MPC）**：培地コスト・培養時間を目的関数に組み込み、収量×品質×コストの Pareto 最適化。
- **品質項の統合**：offline OCT4/SOX2/NANOG 等を目的関数に追加（run 単位評価）。
- **GMP-ready 文書化**：静的・決定論的モデルとしての MPC 仕様、検証証拠、性能等価性、XAI（MPC の予測軌道可視化）。

---

## 3. 技術的詳細

### 3.1 MPC モデル候補

| モデルタイプ | 適用場面 | 長所 | 短所 | iPSC への適合 |
|---|---|---|---|---|
| **線形 MPC (LMPC)** | 初期導入・データが少ない時 | 凸問題・大域最適・実装容易 | 非線形（Monod 阻害・凝集体）を無視 | 限定的（高密度域で非線形顕在） |
| **非線形 MPC (NMPC)** | 中～高密度域、凝集体形成 | 物理法則をそのまま反映 | 求解コスト・局所最適・検証重い | 中（plant_model ODE を流用可） |
| **ハイブリッド MPC（PINN + ODE）** | データが蓄積後 | 物理 + データ、外挿性能 | 50–100 バッチ必要、実装複雑 | 将来（Phase 3） |
| **データ駆動 MPC（DARX/サブスペース）** | 個別細胞株・ドナー変動大 | 適応的・パーソナライズ | 外挿弱・プロセスモデル不在 | 参考（Van Beylen 2020） |

### 3.2 推奨実装スタック

- **プロトタイプ**: CasADi + do-mpc
  - Python 上で NMPC を素早く構築可能。
  - `do-mpc` は OPC-UA 接続の基本例を含む〔DTU thesis〕。
- **高性能組み込み**: acados
  - C コード生成、HPIPM QP ソルバー、組み込み向け。
  - 非線形 MPC を実時間で解くのに適する。
- **シミュレーション連携**: `sim/plant_model`（Manstein ODE）を NMPC の内部モデル/低忠実度モデルとして使用。

### 3.3 制約と Human-on-the-loop

- **絶対制約**：MPC は提案する灌流率を `validate_tool_call` の CPP 包絡線内に抑える。包絡線外の提案は Human-on-the-loop 承認へ。
- **ソフト制約**：乳酸目標値・osmolality 目標値を違反ペナルティとして目的関数に組み込む。
- **信頼度スコア**：モデル予測の不確実性（GP 事後分散、PINN 信頼区間、MHE 残差）を信頼度として提示。低信頼度時は人承認。
- **フェイルセーフ**：MPC ソルバーが非収束・異常値を出した場合、L1 は最後の検証済 setpoint または安全側デフォルト灌流率を保持。

---

## 4. 設計への提言

1. **v1 では MPC を導入せず、L1 ルールエンジンを優先**。〔事実：ADR-0001 決定〕
2. **Phase 2 以降の MPC 拡張路線図を設計文書に明記**。特に「灌流率の多変数制約最適化」を将来の L1 拡張機能として位置づける。
3. **MPC の内部モデルには `sim/plant_model`（Manstein ODE）を第一候補**とし、必要に応じてデータ駆動補正（PINN/適応DARX）を追加。
4. **CHO/mAb 由来の改善率（2% タイトル向上等）は iPSC 目的関数に転用せず**、iPSC 固有の指標（VCD、viability、凝集体径、未分化マーカー）で再定義する。
5. **MPC の導入は必ず Human-on-the-loop・承認ワークフロー内で行う**。Annex 22 対応の決定論的コアとして設計する。

---

## 5. 未確定事項・リスク

| # | 未確定事項 | 影響 | 次ステップ |
|---|---|---|---|
| U1 | iPSC 凝集体特有の動的モデル（特に凝集体形成・シア応答） | MPC 予測精度 | plant_model 拡張または実データ同定 |
| U2 | Raman ベース in-line glucose/lactate の iPSC 校正精度 | 状態推定の質 | Raman 校正実験（別エージェント調査） |
| U3 | MPC 目的関数の重み（収量 vs 品質 vs コスト） | 最適化方向性 | 研究者ヒアリング |
| U4 | 求解時間と cadence（分単位 vs 時間単位） | 制御性能・実装 | do-mpc/acados プロトタイプ |
| U5 | Annex 22 下での MPC 検証戦略 | GMP 移行性 | GAMP5 Cat.4/5 文書化計画 |
| U6 | 細胞保持デバイス（ATF/TFF/重力沈降）の動態とシア | 灌流率上限 | デバイス実証 |

---

## 6. 出典

| ID | タイトル | URL/DOI/PMID/PMCID | 確度 |
|---|---|---|---|
| Manstein 2021 | Manstein & Zweigerdt 2021, Stem Cells Transl Med / STAR Protocols | DOI 10.1002/sctm.20-0453; PMID 33660952; PMC8666714 | 事実 |
| Huang 2020 | Process development and scale-up of pluripotent stem cell manufacturing | DOI 10.18063/cgti.v1.i1.1784; https://www.insights.bio/cell-and-gene-therapy-insights/journal/article/1784/ | 事実 |
| Van Beylen 2020 | Lactate-Based Model Predictive Control Strategy of Cell Growth for Cell Therapy Applications | DOI 10.3390/bioengineering7030078 | 事実 |
| Rashedi 2022 | Model Predictive Controller Design for Bioprocesses (DYCOPS-2022) | https://skoge.folk.ntnu.no/prost/proceedings/dycops-2022/files/0202.pdf | 事実 |
| Report MPC | フィジカルAI包括調査レポート §6.1 | /home/sin/Downloads/report/report.md | 事実 |
| Konstantinov 2006 | The "push-to-low" optimization of high cell density perfusion cultures | Konstantinov et al. 2006（CSPR 概念） | 推定 |
| PSE review | Continuous perfusion cultures are MIMO systems | https://psecommunity.org/wp-content/plugins/wpor/includes/file/2006/LAPSE-2020.0565-1v1.pdf | 事実 |
| do-mpc | do-mpc documentation / batch reactor example | https://www.do-mpc.com/en/latest/example_gallery/batch_reactor.html | 事実 |
| CasADi | CasADi symbolic framework | https://web.casadi.org/ | 事実 |
| acados | acados fast embedded solvers | https://docs.acados.org/ | 事実 |

---

*本レポートは A 層（iPSC 浮遊/凝集体バイオリアクター制御）に限定。CHO/mAb 由来の数値を iPSC にそのまま転用しない。*
