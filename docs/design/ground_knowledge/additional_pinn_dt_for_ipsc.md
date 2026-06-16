# PINN / デジタルツインの iPSC 培養への適用

> **担当**: PINN/digital twin for iPSC（追加調査 Agent Swarm）  
> **Mode**: A 層制御システム追加調査レポート  
> **Date**: 2026-06-16  
> **Scope**: iPSC 浮遊/凝集体バイオリアクター制御（Manstein 型灌流 0→7 vvd、目標密度 ~35×10⁶ cells/mL）  
> **Premise**: ADR-0001（L0 局所 PID + L1 決定的レシピ/ルール + L2 ベイズ最適化 + L3 薄い LLM オーケストレータ）、R&D 一次、Human-on-the-loop

---

## 1. Executive Summary

本調査は、`docs/design/additional_tasks_memo.md` における「PINN / デジタルツインの iPSC 培養への適用」ドメインを補完するものである。

**結論**:

1. **iPSC 浮遊灌流プロセスへの PINN/ハイブリッド DT 適用は、現時点で産業実証例が極めて少ない**。文献のほとんどは CHO fed-batch または微生物培養であり、iPSC 凝集体培養にそのまま転用できない。〔事実：文献サーベイ〕
2. **auto_cell の現行 plant_model（Manstein 2021 ベース 6 項 Monod ODE）は、Phase 1 で十分に機能する決定的検証リグ**である。PINN/DT への拡張は、**Phase 2 以降の将来技術**として位置づけるのが妥当。〔推定：ADR-0001; alignment_with_downloaded_report.md〕
3. **データ要件はハイブリッドモデルで 50–100 バッチ、純粋 NN では 200–500 バッチ**とされており、R&D 一次の初期フェーズではハイブリッドアプローチ（ODE + NN）が現実的。〔推定：Bioprocesstools 2026 サーベイ〕
4. **不確実性定量化（95% 信頼区間）は、Bayesian PINN、Deep Ensemble、EFI など複数アプローチが存在するが、iPSC 培養への検証は未確定**。Human-on-the-loop には「高不確実性時は人へエスカレーション」が必須。〔推定：Shih et al. 2025; 一般知見〕
5. **多忠実度 BO との連携は、Tier2 plant_model を低忠実度、実 run を高忠実度として統合する形が最も現実的**。ただし、低忠実度シミュレータのバイアス（例：mAb 濃度予測で最大 15% 誤差）を考慮した補正モデルが必要。〔推定：Bioprocess Intl 2026; Nobar et al. 2025〕

**設計への影響**:

- v1（Phase 1）: Manstein ODE ベースの `plant_model` を維持。PINN/DT は導入しない。
- Phase 2（12–24 ヶ月）: データが 30–50 run 蓄積した段階で、**ODE + NN ハイブリッドサロゲート**のプロトタイプを検討。主目的は L2 BO の低忠実度評価精度向上。
- Phase 3（24–48 ヶ月）: 不確実性定量化を含む**ハイブリッド DT + MPC** を検討。ただし、Critical 制御経路は依然として決定的コア（L0/L1）に留め、DT はアドバイザリ/承認仲介に限定。

---

## 2. 背景：レポート主張と auto_cell 設計のギャップ

### 2.1 ダウンロードレポートの主張

`/home/sin/Downloads/report/report.md`（フィジカルAI包括調査レポート）は以下を主張している（`docs/design/alignment_with_downloaded_report.md` 経由）：

- PINN/デジタルツインは TRL 5–6、外挿性能とデータ効率性の両立。〔推定：レポート §4.4〕
- Phase 2（12–24 ヶ月）で PINN ベース DT + MPC、Phase 3 で RL。〔推定：レポート §6.2〕
- データ要件として 50–100 バッチを示唆。〔推定：レポート §4.4〕

### 2.2 auto_cell 設計との相違

| 項目 | レポート主張 | auto_cell 設計 | 補完点 |
|---|---|---|---|
| 対象プロセス | CHO/mAb fed-batch 中心 | iPSC 浮遊/凝集体灌流 | CHO 由来のモデル構造/数値を iPSC に転用しない |
| plant_model | PINN/ハイブリッド DT | Manstein ODE（決定的） | ODE → PINN への段階的拡張路線 |
| データ要件 | 50–100 バッチ | R&D 一次で未蓄積 | いつ・どの条件でハイブリッド化を始めるか |
| 不確実性 | 将来技術として言及 | BO の GP 事後分布のみ | 95% CI の実装方法 |
| MPC | Phase 2 で推奨 | L1 はルールエンジン | MPC の将来位置づけ |

---

## 3. PINN / ハイブリッドモデルのバイオリアクター適用例

### 3.1 CHO / 哺乳類細胞培養（参考例、iPSC への直接転用不可）

**Yang et al. 2024** は、大規模パイロット CHO fed-batch 培養に PINN ハイブリッドモデルを適用した。少量スケール研究で得られた第一原理知識と、大規模プロセスデータの深層学習を統合し、実世界プロセスデータで検証している。〔事実：DOI 10.1021/acs.iecr.4c01459〕

- **手法**: 第一原理（質量収支、反応速度論）を PINN の物理損失として組み込み、NN が未知の動態を学習。
- **比較対象**: 純粋データ駆動モデル、純粋メカニスティックモデル、その他ハイブリッドモデル。
- **結果**: 各種計測シナリオで正確な予測が可能。細胞培養アナライザーの日次校正で予測精度がさらに向上。
- **iPSC への注意**: CHO の代謝ネットワーク、凝集体形成、品質指標は iPSC と大きく異なる。モデル構造は参考だが、パラメータ・損失関数・状態変数は再設計が必要。〔推定〕

### 3.2 汎用バイオリアクターモデリング

**Thirugnanasambandam et al. 2025** は、汎用バイオリアクター問題向けに「dual-ANN PINN」構造を提案した。状態変数ネットワーク（FFNN-S）と反応速度論ネットワーク（FFNN-R）を分離し、物理法則を損失関数に組み込む。〔事実：DOI 10.1016/j.compchemeng.2025.109354〕

- **ハイライト**:
  - データが希薄な場合でも、通常の ANN より外挿性能が高い。
  - ハイブリッド半パラメトリックモデルと同程度の精度をデータ領域内で示す。
  - しかし、**時変制御入力を伴う高次元状態の複雑問題では、長期外挿で性能が著しく低下**。
- **教訓**: iPSC 灌流培養（時変灌流率、複数代謝物、凝集体径）はまさに「時変制御入力を伴う高次元問題」に該当するため、**訓練ドメイン外への予測は信用できず、Human-on-the-loop が必須**。〔推定〕

### 3.3 デジタルツインの産業例

**Yokogawa Insilico Biotechnology** の「Insilico Digital Twin Factory」は、バイオリアクターのデジタルツインとして商用品がある。〔事実：Yokogawa 2021 プレスリリース; Pharma Manufacturing 2022〕

- **構成**:
  1. **Reactor Model**: batch/fed-batch/continuous の物質収支。
  2. **Extracellular Reaction Model**: 培地中グルタミン分解などの非生体反応。
  3. **Kinetic Cell Model**: ゲノム規模代謝ネットワークモデル + 人工ニューラルネットワーク。
- **データの使い方**:
  - 代謝ネットワークモデルが活性代謝経路を同定（FBA 等）。
  - NN が活性経路の速度論を学習。
  - 「NN に負担させるのは反応速度の推定のみ」という設計により、少ないデータで正確な DT を構築。
- **効果**: プロセス開発・特性評価・スケールアップに必要な実験を最大 50% 削減できるとされる。〔推定：Yokogawa マーケティング主張〕
- **iPSC への注意**: Yokogawa の事例は mAb 製造（CHO 等）中心。iPSC 浮遊凝集体の「凝集体形成動力学」「未分化性品質指標」といった側面はカバーしていない。〔推定〕

### 3.4 iPSC への直接的な先行例

iPSC 浮遊/凝集体培養に PINN またはハイブリッド DT を適用した**公表された学術文献・産業実装は本調査で確認できなかった**。iPSC 大量培養のモデリングは主に：

- **メカニスティック ODE**（Manstein 2021 等）
- **統計モデル/DoE**（Kanda 2022 等）
- **画像ベース品質推定**（morphcls/diffdet）

に限られており、PINN/DT は未開拓に近い。〔事実：Web 検索・KG サーベイ〕

---

## 4. データ要件と R&D 一次の整合性

### 4.1 機械学習手法別のデータ要件

Bioprocesstools の産業サーベイ（2026）によれば、バイオプロセス最適化の ML 手法別データ要件は以下の通り。〔推定：Bioprocesstools 2026〕

| 手法 | 用途 | データ要件 | 典型 R² | 強み |
|---|---|---|---|---|
| ベイズ最適化（GP） | 培地/プロセススクリーニング | 5–30 実験 | N/A（最適化） | 最適点への実験回数が少ない |
| Random Forest / XGBoost | 収率/CQA 予測 | 50–200 バッチ | 0.85–0.94 | 欠損データ対応、特徴量重要度 |
| ニューラルネットワーク（MLP） | 非線形プロセス写像 | 200–500 バッチ | 0.88–0.95 | 汎関数近似 |
| **Hybrid ODE + NN** | 動的プロセス予測 | **50–100 バッチ** | **0.90–0.97** | 物理制約付き、少ないデータで可 |
| **Physics-informed NN（PINN）** | Fed-batch 動態 | **30–80 バッチ** | **0.92–0.96** | 質量/エネルギー収支を埋め込み |
| 強化学習 | リアルタイム給餌制御 | シミュレータ + 10–50 バッチ | N/A（制御） | バッチ間変動への適応 |
| RNN（LSTM） | 時系列予測 | 100–300 バッチ | 0.87–0.93 | 時間依存性の把握 |

### 4.2 R&D 一次との整合性

auto_cell A 層は R&D 一次（プロセス開発段階）を前提とする。v1 時点では過去 run データが 0 または少数の状況で運用を開始する可能性が高い。

- **Phase 1（0–12 ヶ月）**: Manstein ODE + バッチ BO で十分。PINN は不要。
- **Phase 2（12–24 ヶ月）**: 10–30 run 蓄積時点で、**Hybrid ODE + NN** のプロトタイプを検討可能。ただし、統計的に信頼できるモデル（50 バッチ以上）には至らない可能性が高い。
- **Phase 3（24–48 ヶ月）**: 50–100 run 到達時に、本格的な PINN/ハイブリッド DT の再訓練・検証を実施。

**重要**: 上記データ要件は CHO/mAb または微生物プロセスを対象とした産業経験則であり、**iPSC 浮遊凝集体にそのまま適用する根拠はない**。iPSC では凝集体形成、代謝プロファイル、品質指標の変動が大きく、同等以上のデータが必要と推定される。〔推定〕

---

## 5. plant_model（ODE）から PINN への拡張路線

### 5.1 現行 plant_model の位置づけ

`sim/plant_model` は Manstein 2021 ベースの 6 項 Monod 型 ODE であり、以下の役割を持つ。〔事実：kg_to_auto_cell.md §6〕

- L1 制御ループの検証リグ（CSV/CSA 観点）。
- L2 BO の低忠実度サロゲート。
- 決定的 `step(actuators) -> sensors` IF。

### 5.2 拡張フェーズ

```
Phase 1: Manstein ODE（決定的、文献値固定）
   ↓ 実 run データ蓄積
Phase 2: ベイズパラメータ同定 / GP バイアス補正
   ↓ 50+ run 蓄積
Phase 3: Hybrid ODE + NN（一部 kinetic term を NN で置換）
   ↓ 100+ run 蓄積・検証完了
Phase 4: PINN / Digital Twin（物理損失 + データ損失、不確実性付き）
```

### 5.3 各フェーズの詳細

#### Phase 2: ベイズパラメータ同定 / GP バイアス補正

- **目的**: Manstein ODE の定数（µmax, K_Glc 等）を、実 run データでベイズ推定または最小二乗で校正する。
- **手法**: パラメータ事後分布を推定し、予測に GP バイアス項を加える。
- **不確実性**: パラメータ事後分散から予測区間を計算。
- ** Human-on-the-loop**: 高不確実性時は BO 提案を人へエスカレーション。

#### Phase 3: Hybrid ODE + NN

- **手法**: Monod 式の比増殖速度 µ(S) や、代謝物消費速度 q_Glc, q_Lac 等を、NN で置換または補正する。
- **例**: Universal Differential Equation（UDE）

  ```
  dX/dt = (µ_NN(S, DO, pH) - µ_d) * X
  dGlc/dt = -q_Glc_NN(S, X) * X + F_in/V * (Glc_in - Glc)
  ```

- **利点**: 物理法則（質量収支）を保持しつつ、複雑な代謝応答をデータから学習。
- **課題**: 識別可能性、外挿性能、トレーニングコスト。

#### Phase 4: PINN / Digital Twin

- **手法**: 状態変数を NN で直接表現し、物理残差（ODE 残差）を損失に加える。
- **dual-ANN 構造**: Thirugnanasambandam 2025 に倣い、状態ネットワークと反応速度論ネットワークを分離。
- **入力**: 初期状態 x₀、操作変数 u(t)（灌流率、撹拌、DO setpoint 等）、時間 t。
- **出力**: 状態軌道 X(t) = [VCD, glucose, lactate, glutamine, osmolality, aggregate_diameter]。
- **物理損失**: Manstein ODE の残差を最小化。
- **データ損失**: 観測値（capacitance, Raman, Nova FLEX2, 画像）との誤差を最小化。

### 5.4 iPSC 特異性への対応

iPSC 浮遊凝集体では、以下の項を追加または修正する必要がある。〔推定〕

| iPSC 特異性 | ODE/PINN への反映 |
|---|---|
| 凝集体形成・合体・破砕 | aggregate_formation_model サブネットワーク追加 |
| シアストレス | shear_stress_model から死亡率 µ_d を推定 |
| 未分化性/自発分化 | 品質状態変数を追加（ただし offline ラベルが必要） |
| ゲノム規模代謝 | 将来 COBRApy + GEM 統合 |

---

## 6. 不確実性定量化（95% 信頼区間）

### 6.1 必要性

- R&D 一次でも、モデル予測に基づく BO 提案や MPC 操作は、**予測信頼度が低い領域では人の承認が必須**。
- 将来的な GMP 移行を見据え、モデル予測の信頼区間を文書化しておくことが望ましい。

### 6.2 実装アプローチ

| 手法 | 概要 | 長所 | 短所 | iPSC 適用度 |
|---|---|---|---|---|
| **Bayesian PINN（B-PINN）** | NN 重みの事後分布を変分推定 | 原理的に整備 | 計算コスト高、事前分布選択が主観的 | 未検証 |
| **Deep Ensemble** | 複数 NN を独立学習し予測分布を構成 | 実装が簡単 | 計算コスト、過大/過小評価のリスク | 推奨（最初の一歩） |
| **MC Dropout** | 推論時も dropout を有効化 | 追加コスト少 | dropout 率選択が主観的、区間の質が不安定 | 注意 |
| **EFI（Extended Fiducial Inference）** | データ生成方程式を解く統計推論 | 事前分布不要で理論的に整備 | 新手法、実装例が少ない | 注目 |
| **GP バイアス補正** | ODE 予測残差を GP でモデル化 | 既存 BO インフラと統合しやすい | 低 run 数では表現力に限界 | Phase 2 で推奨 |

### 6.3 Shih et al. 2025 の知見

**Shih, Jiang & Liang 2025** は、PINN の不確実性定量化に Extended Fiducial Inference（EFI）を適用した。〔事実：arXiv 2505.19136; NeurIPS 2025〕

- **主張**: Bayesian PINN や MC Dropout は、事前分布や dropout 率の選択に主観性があり、「正直な信頼区間」を構築できない。
- **EFI**: 観測データに含まれる誤差を同時に推定し、NN パラメータの不確実性を定量化。事前分布を必要としない。
- **結果**: 1D-Poisson モデルで、EFI は 95% 信頼区間のカバレッジ率 0.948、PINN（dropout なし）は 0.095 と大きく改善。
- **iPSC への注意**: 合成問題での検証。バイオリアクター時系列への適用は未確定。〔推定〕

### 6.4 auto_cell への推奨

**Phase 2 から導入可能な現実的アプローチ**:

1. **GP バイアス補正**: Manstein ODE の予測残差を GP で学習。BO の不確実性と自然に統合。
2. **Deep Ensemble**: Hybrid ODE + NN の複数インスタンスを学習。予測の平均と分散から信頼区間を構成。
3. **Human-on-the-loop 閾値**: 95% 信頼区間が CPP 包絡線を跨ぐ場合、または予測分散が閾値を超える場合は人へ承認要求。

---

## 7. 多忠実度 BO との連携

### 7.1 基本構想

既存設計では、`tier2_plant_model`（Manstein ODE）を低忠実度、実バイオリアクタ run を高忠実度として L2 BO に統合する方針がある。〔事実：ADR-0001; kg_to_auto_cell.md §6〕

PINN/DT を導入することで、低忠実度評価の選択肢が拡張する：

| 忠実度 | モデル | コスト | 精度 | 用途 |
|---|---|---|---|---|
| 低 | Manstein ODE | ~秒 | 中（構造的簡略化） | 広範囲スクリーニング |
| 中 | Hybrid ODE + NN | ~分（推論） | 中～高 | 絞り込んだ領域の詳細評価 |
| 高 | 実バイオリアクタ run | ~日 | 最高 | 最終候補の検証 |

### 7.2 低忠実度モデルのバイアス補正

**Nobar et al. 2025** は、デジタルツイン推定値を実データで補正する「guided multi-fidelity BO」を提案。〔事実：arXiv 2509.17952〕

- **問題**: シミュレータと実機の間にモデルミスマッチがある。
- **解決**: 低忠実度モデルの推定に対する補正モデルを学習。適応的取得関数が、改善期待値・忠実度・サンプリングコストをバランス。
- **結果**: ロボット駆動ハードウェアと数値実験で、標準 BO や従来 MF-BO より効率的に制御器チューニング。

**Bioprocess International 2026** のケーススタディでは、CSL Innovation の mAb プロセス（72 run の実データ + メカニスティックシミュレーション）で、MF-BO が追加 4 回の実験で平均 25% の生産性向上を達成。シミュレータの mAb 濃度予測誤差は最大 15%。〔推定：Bioprocess Intl 2026〕

### 7.3 auto_cell への適用

- **低忠実度 1**: Manstein ODE（無償・高速）。
- **低忠実度 2**: Hybrid ODE + NN（Phase 3 以降）。
- **高忠実度**: 実 run。
- **補正モデル**: 低忠実度予測と実 run 結果の差を GP または軽量 NN で学習。
- **取得関数**: MF-GP-UCB、MF-PES、または BoTorch の MF 取得関数。

---

## 8. MPC との連携

### 8.1 レポート主張

レポートは Phase 2 で PINN ベース DT + MPC を推奨している。〔推定：alignment_with_downloaded_report.md §4.4〕

### 8.2 MPC の iPSC 適用の現実性

**Catalão et al. 2025** は、微生物共培養プロセスで PINN を用いた MPC を実装し、PHA 生産能力の制御を行った。〔事実：DOI 10.1016/j.jprocont.2025.103594〕

**Patel et al. 2024** は、DAE 系を PINN でモデル化し、MPC の予測モデルとして使用。〔事実：ADCHEM 2024 Proceedings 0042〕

- ResNet ベース PINN + NTK 勾配更新で、 stiff DAE 系の MPC を実現。
- 数値時間積分を置き換え、高速かつ十分な精度を維持。

**iPSC への注意**:

- 上記は微生物または化学プロセス。哺乳類細胞培養（特に iPSC 凝集体）への MPC 実装例は確認できなかった。
- MPC は run 内の高速な最適化を必要とするが、iPSC 培養の応答は遅い（時間スケールが時間～日）ため、**MPC の差別化価値は限定的**かもしれない。〔推定〕
- **auto_cell では、L1 ルールエンジンでカバーできる範囲が広く、MPC は「灌流率の制約付き最適化」など特定の用途に限定される**。

### 8.3 auto_cell への位置づけ

- **v1/Phase 1**: MPC は導入しない。L1 ルールエンジンで十分。
- **Phase 2/3**: Hybrid ODE + NN が成熟した段階で、**MPC をアドバイザリ層**として検討。例：「今後 24 時間の灌流率プロファイルを最適化」する提案を出し、人が承認。
- **Critical 制御経路**: MPC 出力は L1 の包絡線検証を通過させる。MPC は「提案生成器」、L1 は「最終承認・実行」。

---

## 9. Human-on-the-loop と規制観点

### 9.1 信頼度スコア

- PINN/DT の予測には**信頼度スコア**を付与。
- 信頼度 = 予測の 95% CI 幅、または予測分散の正規化値。
- 低信頼度（例：CI 幅 > CPP 許容範囲の 20%）時は、L3 LLM または HMI が研究者へ承認要求。

### 9.2 決定論的下位層の維持

ADR-0001 の原則を遵守：

- L0/L1 は決定的。
- PINN/DT は L2（run 間最適化）または L3（アドバイザリ）に限定。
- LLM は Critical 制御経路に入れない。

### 9.3 規制対応

- **R&D 一次**: モデルバージョン、訓練データ、ハイパーパラメータ、性能メトリクスを実験記録に保存（ALCOA-lite）。
- **将来 GMP 移行**: モデルは静的・決定論的要素を含む必要がある。PINN 等の確率的要素は「非 Critical アドバイザリ」として扱う。
- **GAMP5 AI/ML Appendix D11**: プロンプト/モデルバージョニング、性能モニタリング、再訓練トリガーを文書化。

---

## 10. 推奨ロードマップ

| フェーズ | 期間 | PINN/DT 活動 | 前提条件 | Human-on-the-loop |
|---|---|---|---|---|
| **Phase 1** | 0–12 ヶ月 | Manstein ODE を維持。PINN/DT は導入しない。 | 5–10 run の運用実績 | 包絡線外 setpoint・trigger_passage・BO 提案を承認 |
| **Phase 2** | 12–24 ヶ月 | GP バイアス補正、ベイズパラメータ同定を導入。Hybrid ODE + NN の PoC。 | 30+ run 蓄積、Nova/Raman 校正完了 | 高不確実性予測時の BO 提案承認 |
| **Phase 3** | 24–48 ヶ月 | Hybrid ODE + NN を L2 BO の低忠実度モデルとして本格運用。PINN/DT + MPC のアドバイザリ機能を検討。 | 50–100 run 蓄積、構造候補モデルの検証 | MPC 提案、DT ベース異常検知の承認 |

---

## 11. 未確定事項・リスク

| # | 項目 | リスク | 次ステップ |
|---|---|---|---|
| U1 | iPSC 浮遊凝集体固有の PINN 構造 | CHO 構造を転用できない | 小規模実データでの構造比較 |
| U2 | データ効率性 | 50–100 バッチは CHO 基準 | iPSC での実証実験 |
| U3 | 外挿性能 | 訓練域外で予測が破綻 | ドメイン適応・Online 更新 |
| U4 | 不確実性定量化の校正 | 95% CI の実際カバレッジが不明 | Retrospective バリデーション |
| U5 | 計算コスト | PINN 推論が BO/MPC の時間制約を圧迫 | 軽量 NN・アンサンブル数の最適化 |
| U6 | 品質指標の予測 | OCT4/SOX2 等は offline ラベル | 画像代理指標との紐付け |

---

## 12. 出典

| ID | タイトル | URL/DOI/PMID/PMCID | 確度 |
|---|---|---|---|
| Manstein 2021 | Manstein & Zweigerdt 2021, Stem Cells Transl Med / STAR Protocols | DOI 10.1002/sctm.20-0453; PMC8666714 | 事実 |
| Thirugnanasambandam 2025 | A Physics-Informed Neural Network (PINN) framework for generic bioreactor modelling | DOI 10.1016/j.compchemeng.2025.109354 | 事実 |
| Yang 2024 | Hybrid Modeling of Fed-Batch Cell Culture Using Physics-Informed Neural Network | DOI 10.1021/acs.iecr.4c01459 | 事実 |
| Catalão 2025 | Bioprocess model-predictive control with physics-informed neural networks | DOI 10.1016/j.jprocont.2025.103594 | 事実 |
| Patel 2024 | Model Predictive Control Using Physics Informed Neural Networks | ADCHEM 2024, https://skoge.folk.ntnu.no/prost/proceedings/adchem-2024/files/0042.pdf | 事実 |
| Shih 2025 | Uncertainty Quantification for Physics-Informed Neural Networks with Extended Fiducial Inference | arXiv 2505.19136 | 事実 |
| Nobar 2025 | Guided Multi-Fidelity Bayesian Optimization for Data-driven Controller Tuning with Digital Twins | arXiv 2509.17952 | 事実 |
| Bioprocesstools 2026 | AI and Machine Learning for Bioprocess Optimization | https://bioprocesstools.com/blog/ai-machine-learning-bioprocess-optimization/ | 推定 |
| Bioprocess Intl 2026 | Doing More with Less: Multifidelity Optimization in the Biopharmaceutical Industry | https://www.bioprocessintl.com/qa-qc/doing-more-with-less-multifidelity-optimization-in-the-biopharmaceutical-industry/ | 推定 |
| BO Guide 2025 | A Guide to Bayesian Optimization in Bioprocess Engineering | arXiv 2508.10642 | 推定 |
| Yokogawa 2021 | Yokogawa Acquires Insilico Biotechnology | https://www.yokogawa.com/news/press-releases/2021/2021-11-02/ | 事実 |
| Yokogawa Pharma 4.0 | Building Intelligent processes for Pharma 4.0 | https://www.yokogawa.com/library/resources/media-publications/building-intelligent-processes-for-pharma-40/ | 推定 |
| Pharma Manufacturing 2022 | Pharma Innovation Awards 2022 | https://www.pharmamanufacturing.com/home/article/21437943/pharma-innovation-awards-2022 | 推定 |
| ADR-0001 | Control architecture — thin LLM orchestrator over deterministic tools + Bayesian optimization | `docs/design/adr/0001-control-architecture.md` | 事実 |
| alignment | ダウンロードレポートと auto_cell 設計方向性の照合分析 | `docs/design/alignment_with_downloaded_report.md` | 事実 |

---

*本レポートは A 層（iPSC 浮遊/凝集体バイオリアクター制御）に限定。CHO/mAb 由来の数値を iPSC にそのまま転用しないことを明示する。*
