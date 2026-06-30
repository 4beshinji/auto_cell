# S04 PINN / Hybrid ODE+NN / デジタルツイン調査レポート

> **担当**: PINN / Hybrid DT / 不確実性定量化調査エージェント  
> **Scope**: auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御、Manstein 型灌流 0→7 vvd）  
> **Date**: 2026-06-30  
> **前提**: ADR-0001、kg_to_auto_cell.md、additional_pinn_dt_for_ipsc.md、additional_investigation_integrated.md §3、02_missing_assets_for_closed_loop.md C4

---

## Executive Summary

1. **iPSC 浮遊/凝集体灌流プロセスへの PINN/Hybrid DT の直接適用例は、公表文献・産業実装ともに本調査で確認できなかった**〔事実：Web 検索・文献サーベイ〕。先行例は CHO fed-batch、微生物培養、クロマトグラフィーが中心であり、iPSC 凝集体形成・未分化性品質指標をカバーした構造は存在しない。〔推定〕
2. **現行の Manstein 2021 6 項 Monod ODE は Phase 1 の決定的検証リグとして十分**〔事実：kg_to_auto_cell.md §4.1〕。PINN/DT 導入は Phase 2 以降の将来技術と位置づけるのが妥当。〔推定：ADR-0001〕
3. **Hybrid ODE+NN は最も現実的な拡張路線**〔推定〕。質量収支・Monod 骨格を保持しつつ、比増殖速度 µ、比代謝速度 q、凝集体形成項などを NN で置換または補正する。データ要件は CHO 基準で 50–100 バッチとされ、iPSC では同等以上が必要。〔推定：Bioprocesstools 2026; Yang 2024; Thirugnanasambandam 2025〕
4. **30 run 未満の初期段階では GP バイアス補正が最も実用的**〔推定〕。Hybrid ODE+NN や PINN を安定的に訓練するには不十分。GP 事後分散は既存 BO インフラと自然に統合できる。〔推定：Siska 2026; 一般知見〕
5. **不確実性定量化は Deep Ensemble または GP バイアス補正から始めるのが現実的**〔推定〕。Bayesian PINN は計算コスト高、MC Dropout は主観的ハイパーパラメータに依存、Evidential Deep Learning（EFI/DER）は有望だが最適化が難しく iPSC バイオリアクターへの検証は未確定。〔推定：Shih 2025; Meinert 2023; Amini 2020〕
6. **MPC 統合は「アドバイザリ層」に限定すべき**〔推定〕。iPSC 培養は時間〜日スケールの遅い応答であり、L1 決定的ルールエンジンでカバーできる範囲が広い。PINN を MPC 内部モデルにする場合、訓練 MV 範囲外での外挿破綻が最大のリスク。〔推定：Patel 2024; kg_to_auto_cell.md §7.2〕

---

## 1. バイオプロセス PINN/Hybrid 事例

| 論文 | 対象プロセス | 構造 | データ量 / 規模 | 主な結果 | 出典 |
|---|---|---|---|---|---|
| **Yang et al. 2024** | CHO fed-batch 大規模パイロット | PINN ハイブリッド。小規模第一原理知見を大規模データの深層学習と統合。質量収支・反応速度論を物理損失として組み込み。 | 製造スケール実データ、複数計測シナリオ | 純データ駆動・純メカニスティック・他ハイブリッドと比較して優位。細胞培養アナライザーの日次校正でさらに精度向上。 | DOI 10.1021/acs.iecr.4c01459 〔事実〕 |
| **Thirugnanasambandam et al. 2025** | 汎用バイオリアクター（2 ケーススタディ：微生物成長、タンパク分泌） | **dual-ANN PINN**: 状態変数ネットワーク（FFNN-S）＋反応速度論ネットワーク（FFNN-R）。物理法則を損失に組み込む。 | データ希薄領域も評価 | データ領域内ではハイブリッド半パラメトリックと同程度。だが**時変制御入力を伴う高次元問題では長期外挿で性能著しく低下**。 | DOI 10.1016/j.compchemeng.2025.109354 〔事実〕 |
| **Patel et al. 2024** | 化学プロセス（CSTR、電気化学 DAE） | ResNet ベース PINN + NTK 勾配更新。DAE/ODE の数値時間積分を PINN で置換。 | 数値実験（CSTR: 12,800 サンプル、DAE: 10,000 サンプル） | MPC の予測モデルとして使用可能。ただし**訓練した MV 範囲外では予渪が大きく外れる**。 | ADCHEM 2024 Proceedings 0042 〔事実〕 |
| **Tang et al. 2025** | 周期逆流クロマトグラフィー（PCC） | PINN ベース General Rate Model。数値解を代替。 | 工業バイオ製造 | オフラインfitting時間を 2,608.6 s → 110.7 s に短縮。オンラインシミュレーション 12–14 s。 | DOI 10.1016/j.chroma.2024.466565 〔事実〕 |
| **Catalão et al. 2025** | 微生物共培養 PHA 生産 | PINN を MPC の予測モデルとし、微生物叢進化を制御。 | 実験＋シミュレーション | PINN-MPC で PHA 生産能力制御を実証。 | DOI 10.1016/j.jprocont.2025.103594 〔事実〕 |
| **Yokogawa Insilico Biotechnology** | mAb 製造（CHO 等）向けデジタルツイン | 反応器モデル＋細胞外反応モデル＋GEM+ANN  kinetic cell model。 | 産業事例（実験最大 50% 削減とされる） | **NN に負担させるのは反応速度推定のみ**という設計で少ないデータで DT 構築。 | Yokogawa 2021 プレスリリース; Pharma Manufacturing 2022 〔事実/推定〕 |
| **Malani et al. / ODEnet** | 哺乳類細胞培養（CHO 等） | ODEnet: ODE 右辺を NN で学習。質量収支に組み込み。 | 時系列データ | 欠損観測・任意サンプリング間隔に対応。物理知識を導入することでデータ効率向上。 | Ranpura 2025 レビュー 〔推定〕 |
| **Bangi et al. / UDE** | *Saccharomyces cerevisiae* バッチ発酵 | Universal Differential Equation（UDE）。既知機構＋NN で未知動態を学習。 | 発酵データ | 深い NN を用いた UDE が浅いハイブリッドより汎化しやすいとされる。 | Pinto 2023 プリプリント; Bangi 2022 〔推定〕 |

### iPSC への転用注意（CHO/microbial 例から）

| 転用項目 | 注意事項 | 確度 |
|---|---|---|
| 代謝プロファイル | CHO の乳酸蓄積・グルコース要求量は iPSC と異なる。Manstein モデル値（K_Glc=1.5 mM, K_Lac=50 mM）を出発点としつつ、実株で再校正が必須。 | 事実（Manstein 2021; kg_to_auto_cell.md §5） |
| 凝集体形成動態 | CHO は単一懸濁が基本。iPSC は凝集体形成・合体・破砕が品質・酸素拡散・シアを規定。これを PINN に組み込む構造例は未公表。 | 推定 |
| 品質指標 | mAb タイトルや糖鎖パターンではなく、収量 × 生存率 × 多能性マーカー × 凝集体サイズが目的。オフラインラベルが必要。 | 推定（kg_to_auto_cell.md §4.3） |
| シア応答 | 攪拌 rpm・tip speed・EDR と増殖/凝集体径の定量式は細胞株・リアクター形状に強く依存。CHO 値を転用不可。 | 推定（Borys 2021; Lee 2022） |

---

## 2. iPSC への転用可能性評価

### 2.1 現状

- **iPSC 浮遊/凝集体灌流培養に PINN または Hybrid ODE+NN を直接適用した公表例はない**〔事実〕。
- iPSC 大量培養のモデリングは **メカニスティック ODE（Manstein 2021）**、**統計モデル/DoE（Kanda 2022）**、**画像ベース品質推定**に限られている〔推定：additional_pinn_dt_for_ipsc.md §3.4〕。

### 2.2 転用可能性マトリクス

| 技術要素 | iPSC 転用可否 | 理由 |
|---|---|---|
| 質量収支・Monod 骨格 | ◎ | Manstein 2021 が既に iPSC hPSC 灌流培養で検証済み。 |
| 比増殖速度 µ の NN 置換 | △ | 構造的には可能。外挿性能と識別可能性が課題。 |
| 凝集体形成・合体項 | ×（未確定） | iPSC 特異的現象で、先行 PINN 構造は未カバー。 |
| シアストレス誘導死亡率 | △ | 定量式が未確立。EDR 範囲などの代理指標から構築が必要。 |
| 未分化性/品質状態変数 | ×（未確定） | ラベルが offline/run 単位。run 内予測は画像代理指標が必要。 |
| GEM（COBRApy）統合 | △（将来） | ゲノム規模代謝モデルは将来拡張。iPSC 特異 GEM が必要。 |

### 2.3 結論

iPSC への転用は **構造的再設計が必須**であり、CHO/microbial 事例は「構造パターン」の参考に留める。〔推定〕

---

## 3. 推奨モデル構造（Hybrid ODE+NN）

### 3.1 設計思想

- **保存則は維持**：質量収支、細胞数収支、代謝物収支は ODE のまま。
- **NN が学ぶのは「未知の動態」**：比増殖速度 µ、代謝速度 q、凝集体形成速度、シア応答など。
- **物理損失＋データ損失の両方を最小化**。

### 3.2 状態変数と入力

状態ベクトル:

```
x(t) = [X_v, G, L, Q, O, A, DO, pH]^T
```

| 記号 | 説明 | 単位 |
|---|---|---|
| X_v | Viable cell density | cells/mL |
| G | Glucose concentration | mM |
| L | Lactate concentration | mM |
| Q | Glutamine concentration | mM |
| O | Osmolality | mOsm/kg |
| A | Aggregate diameter | µm |
| DO | Dissolved oxygen | % |
| pH | pH | - |

操作変数:

```
u(t) = [F_p(t), N(t), DO_sp(t), pH_sp(t), G_feed(t), Q_feed(t)]^T
```

| 記号 | 説明 | 単位 |
|---|---|---|
| F_p | Perfusion rate | vvd |
| N | Agitation speed | rpm |
| DO_sp | DO setpoint | % |
| pH_sp | pH setpoint | - |
| G_feed | Glucose bolus feed | mM/day |
| Q_feed | Glutamine bolus feed | mM/day |

### 3.3 Hybrid ODE+NN 方程式

#### 基本形（Universal Differential Equation）

```
dx/dt = f_known(x, u, θ_M) + f_NN(x, u, θ_NN)
```

ここで `f_known` は既知の質量収支項、`f_NN` は NN が学習する補正項または未知動態項。

#### 各状態の具体例

```
dX_v/dt = [µ_NN(x, u) - µ_d_NN(x, u)] · X_v - (F_p/V) · X_v

dG/dt = -q_Glc_NN(x, u) · X_v + (F_p/V) · (G_in - G) + G_feed/V

dL/dt = +q_Lac_NN(x, u) · X_v - (F_p/V) · L

dQ/dt = -q_Gln_NN(x, u) · X_v + (F_p/V) · (Q_in - Q) + Q_feed/V

dO/dt = f_Osm(G, L, Q, F_p, ...) + δ_O_NN(x, u)

dA/dt = f_agg_NN(x, u)          # 凝集体形成・合体・破砕

dDO/dt = f_DO_known(DO, N, DO_sp) + δ_DO_NN(x, u)

dpH/dt = f_pH_known(pH, CO2, pH_sp) + δ_pH_NN(x, u)
```

#### NN の入出力

```
# 比速度 NN（例）
[µ, q_Glc, q_Lac, q_Gln] = NN_µq(x_in; θ_µq)

# 凝集体動態 NN（例）
dA/dt = NN_agg(x_in; θ_agg)

# 補正 NN（例）
δ_O, δ_DO, δ_pH = NN_corr(x_in; θ_corr)
```

入力 `x_in` は以下を含む:

```
x_in = [log(X_v), G, L, Q, O, A, DO, pH, F_p, N, DO_sp, pH_sp, t]
```

対数変換は細胞密度の広い動的範囲に対応。〔推定〕

### 3.4 損失関数

```
L = w_data · L_data + w_phys · L_phys + w_reg · L_reg + w_pos · L_pos
```

各項:

```
L_data = (1/N_data) Σ ||x_pred(t_i) - x_obs(t_i)||²
L_phys = (1/N_coll) Σ ||dx_pred/dt - f(x_pred, u, θ)||²
L_reg  = λ · ||θ_NN||²
L_pos  = Σ max(0, -X_v)² + Σ max(0, -G)² + ...  # 非負制約
```

### 3.5 構造図

```
                          ┌─────────────────┐
         u(t) ───────────▶│                 │
                          │   Manstein      │
         x(0) ───────────▶│   ODE Core      │────┐
                          │   (f_known)     │    │
                          └─────────────────┘    │
                                    │            │
                                    ▼            │
                          ┌─────────────────┐    │
                          │  NN surrogate   │    │
                          │  (µ, q, f_agg)  │    │
                          │  + correction   │◀───┘
                          └─────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │  ODE Solver     │
                          │  (torchdiffeq/  │
                          │   scipy)        │
                          └─────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │  x_pred(t)      │
                          │  + uncertainty  │
                          └─────────────────┘
```

---

## 4. PINN フレームワーク比較

| フレームワーク | 特徴 | 長所 | 短所 | iPSC 適用推奨度 |
|---|---|---|---|---|
| **DeepXDE** | 最も成熟した PINN ライブラリ。TensorFlow/PyTorch/JAX/PaddlePaddle バックエンド。複雑ドメイン、境界条件、サンプリング、不確実性（dropout）を内包。 | コード量が少ない（PyTorch 自前の 1/3）。PINN 訓練の最適化あり。L-BFGS/NNCG 対応。 | カスタム ODE 構造の柔軟性は PyTorch 自命より劣る。Hybrid ODE+NN には追加実装が必要。 | Phase 3–4 で検討 |
| **NeuroDiffEq** | PyTorch ベース、軽量。 | 使いやすい。Solution Bundle でパラメータ推定可能。 | 本質的には PINN。大規模・複雑制約には機能が限定的。メンテナンス頻度低。 | PoC 用 |
| **PyTorch 自前** | `torch.autograd` で手動実装。 | 最大の柔軟性。Hybrid ODE+NN、UDЕ、Neural ODE に自由に対応。 | 実装・デバッグ・最適化コスト高。 | **Phase 2–3 推奨** |
| **TorchDyn / torchdiffeq** | Neural ODE / UDE 専用。 | ODE ソルバーが高速・高精度。Rackauckas 2020 UDE と親和性高。 | PINN の物理損失は自前で追加。 | **Hybrid ODE+NN Phase 2–3 で推奨** |
| **TensorFlow Probability** | 確率的レイヤー・変分推論。 | Bayesian NN 実装に理論的整備。 | Python 生態系では PyTorch より使われにくい。PINN との統合例が少ない。 | 未推奨 |
| **Julia DiffEqFlux.jl** | UDE/Neural ODE に最適。 | UDE では PINN より「数桁高速」（Rackauckas 2021）。 | Python スタック外。auto_cell 依存に追加言語を入れるコスト。 | 将来検討 |

### 推奨選択

- **Phase 2（GP バイアス補正）**: PyTorch + GPyTorch/BoTorch（追加依存なしで既存 BO インフラ拡張）。
- **Phase 3（Hybrid ODE+NN）**: **PyTorch 自前 + torchdiffeq**。柔軟性と性能のバランスが最良。
- **Phase 4（PINN）**: DeepXDE（PyTorch backend）でプロトタイプし、カスタム要件が増えたら PyTorch 自前へ移行。

---

## 5. 不確実性定量化手法の比較と推奨

| 手法 | 概要 | 長所 | 短所 | iPSC 適用度 |
|---|---|---|---|---|
| **GP バイアス補正** | ODE 予測残差を GP でモデル化。 | BO インフラと自然統合。少データ（<30 run）で動作。 | 低 run 数では表現力に限界。外挿が弱い。 | **Phase 2 推奨** |
| **Deep Ensemble** | 複数 NN を独立学習し予測分布を構成。 | 実装が簡単。多くの領域で最も口径の良い不確実性。 | 計算コスト・メモリが M 倍。過大/過小評価のリスク。 | **Phase 2–3 推奨** |
| **Bayesian PINN (B-PINN)** | NN 重みの事後分布を HMC/VI で推定。 | 原理的に整備。信頼区間の解釈が明確。 | 計算コスト高。事前分布選択が主観的。 | 未検証 |
| **MC Dropout** | 推論時も dropout を有効化。 | 追加コスト少。 | dropout 率選択が主観的。区間の質が不安定。 | 注意 |
| **Evidential Deep Learning (EFI/DER)** | NIG などの分布パラメータを直接学習。 | 単一 forward pass で epistemic/aleatoric 分解。 | 正則化ハイパーパラメータに敏感。理論的限界の指摘あり（Meinert 2023）。iPSC 検証なし。 | 注目・監視 |
| **EFI for PINN (Shih 2025)** | Extended Fiducial Inference を PINN に適用。事前分布不要。 | 95% 信頼区間のカバレッジが合成問題で 0.948 と改善。 | 合成問題のみの検証。バイオリアクター時系列への適用は未確定。 | 注目・監視 |

### 推奨組み合わせ

```
Phase 2:  GP バイアス補正（主） + Deep Ensemble（PoC）
Phase 3:  Deep Ensemble（主） + GP バイアス補正（残差補正）
Phase 4:  Deep Ensemble + EFI/DER or B-PINN（検証後）
```

### Human-on-the-loop 閾値案

```
confidence_score = 1 - (CI_width / CPP_allowable_range)

if confidence_score < 0.5:
    escalate_to_human()
```

または予測分散 σ² が閾値を超える場合にエスカレーション。〔推定〕

---

## 6. 少データ（30 run 未満）での有効な手法

### 6.1 各手法のデータ要件（CHO/microbial 基準）

| 手法 | データ要件 | 典型 R² | 出典 |
|---|---|---|---|
| GP / Bayesian Optimization | 5–30 実験 | N/A（最適化） | Bioprocesstools 2026 〔推定〕 |
| Random Forest / XGBoost | 50–200 バッチ | 0.85–0.94 | Bioprocesstools 2026 〔推定〕 |
| MLP（純粋 NN） | 200–500 バッチ | 0.88–0.95 | Bioprocesstools 2026 〔推定〕 |
| **Hybrid ODE + NN** | **50–100 バッチ** | **0.90–0.97** | Bioprocesstools 2026 〔推定〕 |
| **PINN** | **30–80 バッチ** | **0.92–0.96** | Bioprocesstools 2026 〔推定〕 |

### 6.2 30 run 未満での現実的戦略

| 状況 | 推奨手法 | 理由 |
|---|---|---|
| **<10 run** | Manstein ODE + 手動パラメータフィット | 物理構造が主導。統計的信頼区間は小さくない。 |
| **10–30 run** | **GP バイアス補正** | 非線形補正を少データで学習。BO と統合しやすい。 |
| **20–30 run（質的に均質）** | Hybrid ODE+NN PoC（単一 kinetic term のみ NN 化） | 過学習リスクを抑えるため、未知項を 1–2 個に限定。 |
| **クローン/培地変更時** | 転移学習 | 類似プロセスで事前学習した NN を部分的に fine-tuning。 |

### 6.3 iPSC R&D 早期段階での判断

- **Phase 1（0–12 ヶ月、5–10 run）**: GP バイアス補正すら不要。Manstein ODE をベースに、必要に応じて 1–2 パラメータのベイズ推定または最小二乗フィット。〔推定〕
- **Phase 2（12–24 ヶ月、10–30 run）**: GP バイアス補正を本格導入。Hybrid ODE+NN は小規模 PoC のみ。〔推定〕
- **Phase 2 移行条件**: 30 run 蓄積が一つの目安だが、Hybrid ODE+NN の信頼性を担保するには **50 run 以上**が望ましい。〔推定〕

---

## 7. 多忠実度 BO との連携

### 7.1 忠実度階層案

| 忠実度 | モデル | 計算コスト | 期待精度 | 用途 |
|---|---|---|---|---|
| 低 | Manstein ODE | ~秒 / run | 構造的簡略化によるバイアスあり | 広範囲スクリーニング |
| 中 | Hybrid ODE+NN | ~分 / run（推論） | 中〜高（データ依存） | 絞り込んだ領域の詳細評価 |
| 高 | 実バイオリアクタ run | ~日 / run | 最高 | 最終候補の検証 |

### 7.2 低忠実度モデルの要求精度

- **Bioprocess International 2026 の CSL ケーススタディ**: メカニスティックシミュレータの mAb 濃度予測誤差 **最大 15%** でも、MF-BO は追加 4 回の実験で平均 25% の生産性向上を達成。〔推定：Bioprocess Intl 2026〕
- **auto_cell への示唆**: Manstein ODE の VCD/代謝物予測誤差が **NRMSE 15–20%** 程度であれば、MF-BO の低忠実度モデルとして有用。〔推定〕
- より高い精度が必要な場合、Hybrid ODE+NN によって **NRMSE 5–10%** を目指す。〔推定〕

### 7.3 補正モデル

```
y_high(x) = y_low(x) + δ(x)
δ(x) ~ GP(0, k(x, x'))
```

または NN ベースの補正:

```
y_high(x) = y_low(x) + NN_corr(x)
```

Nobar et al. 2025 の「guided multi-fidelity BO」は、この補正モデルを適応的に学習し、忠実度・コスト・改善期待値をバランスする。〔事実：arXiv 2509.17952〕

### 7.4 取得関数

- **MF-GP-UCB** / **MF-PES** / **BoTorch の MF 取得関数**を検討。
- 低忠実度コストがほぼゼロに近い場合、取得関数は過剰に低忠実度サンプルを選ぶ傾向があるため、コスト調整パラメータの注意が必要。〔推定：BoTorch Discussion #2967〕

---

## 8. MPC との統合

### 8.1 PINN を MPC 内部モデルとする場合のメリット・デメリット

| 項目 | メリット | デメリット |
|---|---|---|
| 計算コスト | 数値積分を bypass し、オンライン最適化を加速可能（Tang 2025: 2608 s → 110 s） | NN 推論コストは低いが、訓練コスト高。MPC 每ステップの forward 評価は許容範囲。 |
| 精度 | 訓練ドメイン内では高い精度を維持 | **訓練 MV 範囲外では外挿破綻**（Patel 2024） |
| 制約処理 | 制約付き最適化に組み込み可能 | 物理的整合性を保つため非負制約等が必要 |
| 保守性 | 再訓練が必要 | ドリフト検知・再訓練基準が必要 |

### 8.2 iPSC 培養における MPC の価値

- iPSC 培養の応答は **時間〜日スケール** であり、秒〜分単位の高速 MPC の差別化価値は限定的。〔推定：additional_pinn_dt_for_ipsc.md §8.2〕
- **L1 決定的ルールエンジン**で glucose/lactate/osmolality トリガーによる灌流制御が可能。
- MPC は **「今後 24 時間の灌流率プロファイル最適化」** など、戦略的アドバイザリとして利用。〔推定〕

### 8.3 推奨アーキテクチャ

```
MPC（Phase 3 アドバイザリ層）
  │
  ├── 内部モデル: Hybrid ODE+NN または Manstein ODE + GP 補正
  │
  ├── 出力: 灌流率/給餌/攪拌の提案軌道 u*(t)
  │
  └── L1 validate_tool_call() で包絡線・ramp 制限検証
           │
           ▼
      人間承認（HITL）
           │
           ▼
      L0/L1 実行
```

---

## 9. sim/real gap 評価指標

### 9.1 推奨メトリクス

| 指標 | 式 | 用途 |
|---|---|---|
| **RMSE** | √(1/N Σ(y_sim - y_real)²) | 絶対誤差。VCD、代謝物共通。 |
| **NRMSE** | RMSE / (y_max - y_min) | 変数間比較。目標 < 10–15%。 |
| **MAPE** | 100/N Σ\|y_sim - y_real\| / y_real | パーセント解釈。y_real ≈ 0 で不安定。 |
| **R²** | 1 - SS_res/SS_tot | 全変動の説明率。目標 > 0.9。 |
| **MAE** | 1/N Σ\|y_sim - y_real\| | 外れ値に強い指標。 |
| **DTW** | Dynamic Time Warping distance | 時系列の形状・位相ずれを評価。 |
| **TDI** | Temporal Distortion Index | 時間同期性の評価。 |

### 9.2 ドリフト検知・再訓練判断基準

| 判定 | 基準 | アクション |
|---|---|---|
| 正常 | NRMSE < 閾値（例：VCD 10%、glucose 15%） | 継続運用 |
| 軽微ドリフト | 連続 M 点で予測残差が最近窓の 95% UCB を超過 | GP 補正モデルを再学習 |
| 顕著ドリフト | NRMSE > 閾値の 2 倍、または CI が CPP 許容範囲を超過 | Hybrid ODE+NN の再訓練、または構造見直し |
| 構造変化 | 新規細胞株/スケール/培地変更 | 新規データ取得後、モデル再構築 |

### 9.3 推奨スライディングウィンドウ法

```python
# 各センサ i について最近 W 点の残差分布をガウス近似
μ_i, σ_i = mean(residuals[-W:]), std(residuals[-W:])
γ_i = μ_i + z_α * σ_i   # 例: z_α = 2 for ~95%

if |δ_t,i| > γ_i:
    flag_drift(sensor=i)
```

〔推定：Ma et al. 2024 Reality Gap Analysis モジュール〕

### 9.4 再訓練トリガー条件（案）

| # | トリガー | 確度 |
|---|---|---|
| T1 | 新しい run が N_run 個（例：5）蓄積し、validation NRMSE が閾値を超過 | 推定 |
| T2 | 細胞株・培地・スケール・装置変更 | 推定 |
| T3 | GP 事後分散が全領域で増大傾向 | 推定 |
| T4 | 予測の 95% CI が CPP 制限値を跨る頻度が増加 | 推定 |

---

## 10. フェーズ別導入ロードマップ

```
Phase 1 (0–12 ヶ月)
  └─ Manstein ODE（決定的、文献値固定）
        └─ L1 決定的レシピ/ルール
        └─ L2 BO の低忠実度サロゲート

Phase 2 (12–24 ヶ月)
  ├─ ベイズパラメータ同定（µmax, K_Glc 等）
  ├─ GP バイアス補正（ODE 残差を GP で学習）
  ├─ Deep Ensemble PoC（Hybrid ODE+NN の複数インスタンス）
  └─ 信頼度スコア層実装

Phase 3 (24–48 ヶ月)
  ├─ Hybrid ODE + NN 本格運用
  │     └─ 比速度 µ, q を NN 化
  │     └─ 凝集体形成項の NN 化（実データ検証後）
  ├─ L2 BO 低忠実度モデルとして統合
  ├─ MPC アドバイザリ機能（灌流率プロファイル最適化）
  └─ ドリフト監視・再訓練基準の運用化

Phase 4 (48 ヶ月〜)
  ├─ PINN / Digital Twin（物理損失＋データ損失）
  ├─ 不確実性定量化の高度化（B-PINN or EFI）
  └─ 経済 MPC（Economic MPC）検討
```

### 各フェーズの詳細

| フェーズ | 期間 | モデル | データ要件 | Human-on-the-loop |
|---|---|---|---|---|
| **Phase 1** | 0–12 ヶ月 | Manstein ODE | 5–10 run | 包絡線外 setpoint、BO 提案、trigger_passage の承認 |
| **Phase 2** | 12–24 ヶ月 | GP バイアス補正 + ベイズパラメータ同定 + Hybrid ODE+NN PoC | 10–30 run | 高不確実性予測時の BO 提案承認 |
| **Phase 3** | 24–48 ヶ月 | Hybrid ODE+NN（L2 BO 低忠実度モデル）+ MPC アドバイザリ | 50–100 run | MPC 提案、DT ベース異常検知の承認 |
| **Phase 4** | 48 ヶ月〜 | PINN/DT + 高度 UQ | 100+ run | 構造変更・再訓練の承認 |

---

## 11. Python 実装方針

### 11.1 依存関係（追加候補）

```toml
[project.optional-dependencies]
pinn = [
    "torch>=2.0",
    "torchdiffeq>=0.2.3",
    "torchdyn>=1.0.6",      # UDE/Neural ODE 用（任意）
    "deepxde>=1.13",        # Phase 4 PINN 用
    "gpytorch>=1.11",       # GP バイアス補正
    "botorch>=0.12",        # MF-BO
]
```

### 11.2 モジュール構成案

```
sim/plant_model/
├── __init__.py                 # Manstein ODE（Phase 1）
├── hybrid_ode_nn.py            # Phase 2–3
├── pinn_model.py               # Phase 4
├── uncertainty/
│   ├── gp_bias.py              # GP バイアス補正
│   ├── deep_ensemble.py        # Deep Ensemble
│   ├── mc_dropout.py           # MC Dropout
│   └── evidential.py           # EFI/DER
├── mpc/
│   └── advisory_mpc.py         # MPC アドバイザリ
└── gap/
    ├── metrics.py              # RMSE/NRMSE/MAPE/DTW
    └── drift_detector.py       # ドリフト検知
```

### 11.3 Hybrid ODE+NN の最小実装パターン

```python
import torch
import torch.nn as nn
from torchdiffeq import odeint

class KineticNN(nn.Module):
    def __init__(self, n_in: int, n_out: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_in, 64), nn.Tanh(),
            nn.Linear(64, 64), nn.Tanh(),
            nn.Linear(64, n_out),
        )

    def forward(self, x_in: torch.Tensor) -> torch.Tensor:
        return self.net(x_in)

class HybridPlant(nn.Module):
    def __init__(self, kinetic_nn: KineticNN, known_params: dict):
        super().__init__()
        self.kinetic_nn = kinetic_nn
        self.params = known_params

    def forward(self, t: torch.Tensor, x: torch.Tensor, u: torch.Tensor) -> torch.Tensor:
        # x: [X_v, G, L, Q, O, A, DO, pH]
        # u: [F_p, N, DO_sp, pH_sp, G_feed, Q_feed]
        x_in = torch.cat([x, u, t.unsqueeze(-1)], dim=-1)
        mu, q_glc, q_lac, q_gln = self.kinetic_nn(x_in).split(1, dim=-1)

        X_v, G, L, Q, O, A, DO, pH = x.unbind(-1)
        F_p, N, DO_sp, pH_sp, G_feed, Q_feed = u.unbind(-1)

        dX_v = (mu - self.params['mu_d']) * X_v - (F_p / self.params['V']) * X_v
        dG   = -q_glc * X_v + (F_p / self.params['V']) * (self.params['G_in'] - G) + G_feed / self.params['V']
        dL   =  q_lac * X_v - (F_p / self.params['V']) * L
        dQ   = -q_gln * X_v + (F_p / self.params['V']) * (self.params['Q_in'] - Q) + Q_feed / self.params['V']
        # ... O, A, DO, pH は同様

        return torch.stack([dX_v, dG, dL, dQ, dO, dA, dDO, dpH], dim=-1)

# 推論
plant = HybridPlant(kinetic_nn, params)
x0 = torch.tensor([[...]])
t = torch.linspace(0, 7, 100)
traj = odeint(lambda t, x: plant(t, x, u_func(t)), x0, t, method='dopri5')
```

### 11.4 学習戦略

| 項目 | 推奨 |
|---|---|
| 損失関数 | `L_data + w_phys * L_phys + w_reg * L_reg + w_pos * L_pos` |
| 重み初期化 | Xavier/Glorot |
| 活性化関数 | Tanh / SiLU（Thirugnanasambandam 2025 は SiLU を使用） |
| 最適化 | Adam → L-BFGS（DeepXDE 推奨パターン） |
| 学習率 | 1e-3（Adam）、段階的減衰 |
| 正則化 | L2（λ=1e-4〜1e-6） + 非負制約 |
| データ拡張 | コロケーション点の適応的再サンプリング |
| 早期停止 | validation NRMSE が 50 epoch 改善しない場合 |

---

## 12. 未確定事項とデータ要件

### 12.1 未確定事項

| # | 項目 | リスク | 次ステップ | 確度 |
|---|---|---|---|---|
| U1 | iPSC 凝集体形成動力学の NN 構造 | 凝集体サイズ予測が破綻 | 小規模実データで構造比較 | 未確定 |
| U2 | データ効率性 | CHO 基準 50–100 バッチが iPSC で十分か不明 | iPSC 実データでの検証 | 推定 |
| U3 | 外挿性能 | 訓練域外で予測が破綻 | ドメイン適応・再訓練戦略 | 推定 |
| U4 | 不確実性定量化の校正 | 95% CI の実際カバレッジが不明 | Retrospective バリデーション | 未確定 |
| U5 | 計算コスト | PINN 訓練が BO/MPC の時間制約を圧迫 | 軽量 NN・ pruning・surrogate 化 | 推定 |
| U6 | 品質指標の予測 | OCT4/SOX2 等は offline ラベル | 画像代理指標との紐付け | 未確定 |
| U7 | シア応答の定量式 | EDR と細胞応答の関係が未確定 | 文献サーチ＋実験 | 未確定 |
| U8 | MPC の Annex 22 分類 | 動的モデルは Critical 用途に不可 | 非 Critical アドバイザリとして運用 | 推定 |

### 12.2 データ要件まとめ

| 用途 | 必要データ量 | ラベル | 備考 |
|---|---|---|---|
| Phase 1 Manstein ODE | 5–10 run | VCD, glucose, lactate, glutamine, osmolality, aggregate diameter | 文献値固定で開始 |
| Phase 2 GP バイアス補正 | 10–30 run | ODE 残差 | BO と統合 |
| Phase 2 Hybrid ODE+NN PoC | 20–30 run（単一 kinetic term） | 状態軌道 | 過学習注意 |
| Phase 3 Hybrid ODE+NN 本格 | 50–100 run | 状態軌道＋操作変数 | CHO 基準 |
| Phase 4 PINN/DT | 100+ run | 同上＋高頻度コロケーション点 | 未検証 |
| 品質代理指標 | 数十〜数百バッチ | offline OCT4/SOX2/NANOG + 画像 | kg_to_auto_cell.md §4.3 |

---

## 13. 出典リスト

| ID | タイトル | URL/DOI/PMID/arXiv | 確度 |
|---|---|---|---|
| Manstein 2021 | High density bioprocessing of hPSCs | DOI 10.1002/sctm.20-0453; PMC8666714 | 事実 |
| Thirugnanasambandam 2025 | A Physics-Informed Neural Network (PINN) framework for generic bioreactor modelling | DOI 10.1016/j.compchemeng.2025.109354 | 事実 |
| Yang 2024 | Hybrid Modeling of Fed-Batch Cell Culture Using Physics-Informed Neural Network | DOI 10.1021/acs.iecr.4c01459 | 事実 |
| Catalão 2025 | Bioprocess model-predictive control with physics-informed neural networks | DOI 10.1016/j.jprocont.2025.103594 | 事実 |
| Patel 2024 | Model Predictive Control Using Physics Informed Neural Networks | ADCHEM 2024, https://skoge.folk.ntnu.no/prost/proceedings/adchem-2024/files/0042.pdf | 事実 |
| Tang 2025 | Developing physics-informed neural networks for model predictive control of periodic counter-current chromatography | DOI 10.1016/j.chroma.2024.466565 | 事実 |
| Shih 2025 | Uncertainty Quantification for Physics-Informed Neural Networks with Extended Fiducial Inference | arXiv 2505.19136 | 事実 |
| Nobar 2025 | Guided Multi-Fidelity Bayesian Optimization for Data-driven Controller Tuning with Digital Twins | arXiv 2509.17952 | 事実 |
| Bioprocesstools 2026 | AI and Machine Learning for Bioprocess Optimization | https://bioprocesstools.com/blog/ai-machine-learning-bioprocess-optimization/ | 推定 |
| Bioprocess Intl 2026 | Doing More with Less: Multifidelity Optimization in the Biopharmaceutical Industry | https://www.bioprocessintl.com/qa-qc/doing-more-with-less-multifidelity-optimization-in-the-biopharmaceutical-industry/ | 推定 |
| Siska 2026 | A Guide to Bayesian Optimization in Bioprocess Engineering | PMC13003447 | 推定 |
| Yokogawa 2021 | Yokogawa Acquires Insilico Biotechnology | https://www.yokogawa.com/news/press-releases/2021/2021-11-02/ | 事実 |
| Borys 2021 | Overcoming bioprocess bottlenecks in large-scale expansion of hiPSC aggregates | DOI 10.1186/s13287-020-02109-4 | 事実 |
| Lee 2022 | Cell Culture Process Scale-Up Challenges for Commercial-scale Manufacturing of allogeneic PSC Products | https://www.regmednet.com/.../Cell-Culture-Process-Scale-up-Challenges... | 事実 |
| Huang 2020 | Process development and scale-up of PSC manufacturing | DOI 10.18063/cgti.v1.i1.1784 | 事実 |
| Rackauckas 2020 | Universal Differential Equations for Scientific Machine Learning | arXiv 2001.04385 | 事実 |
| TorchDyn 2020 | TorchDyn: A Neural Differential Equations Library | arXiv 2009.09346 | 事実 |
| NeuroDiffEq 2020 | NeuroDiffEq: A Python package for solving differential equations with neural networks | Chen et al. 2020 | 事実 |
| DeepXDE 2021 | DeepXDE: A deep learning library for solving differential equations | DOI 10.1137/21M1391332 | 事実 |
| Amini 2020 | Deep Evidential Regression | NeurIPS 2020 | 事実 |
| Meinert 2023 | The Unreasonable Effectiveness of Deep Evidential Regression | NeurIPS 2023 Workshop | 事実 |
| Lakshminarayanan 2017 | Simple and Scalable Predictive Uncertainty Estimation using Deep Ensembles | NeurIPS 2017 | 事実 |
| Gal 2016 | Dropout as a Bayesian Approximation: Representing Model Uncertainty in Deep Learning | ICML 2016 | 事実 |
| Ma 2024 | Bridging the Reality Gap in Digital Twins with Context-Aware, Physics-Guided Deep Learning | arXiv 2505.11847 | 推定 |
| Ranpura 2025 | Wheels turning: CHO cell modeling moves into a digital biomanufacturing era | DOI 10.1016/j.csbj.2025.06.035 | 推定 |
| Pinto 2023 | From Shallow to Deep Bioprocess Hybrid Modeling | preprints.org 202310.0107 | 推定 |
| ADR-0001 | Control architecture — thin LLM orchestrator over deterministic tools + Bayesian optimization | docs/design/adr/0001-control-architecture.md | 事実 |
| kg_to_auto_cell | KG → auto_cell 設計ブリッジ | docs/design/kg_to_auto_cell.md | 事実 |
| additional_pinn | PINN / デジタルツインの iPSC 培養への適用 | docs/design/ground_knowledge/additional_pinn_dt_for_ipsc.md | 事実 |
| additional_integrated | 追加調査統合レポート §3 | docs/design/ground_knowledge/additional_investigation_integrated.md | 事実 |

---

*本レポートは A 層（iPSC 浮遊/凝集体バイオリアクター制御）に限定。CHO/mAb/微生物由来の数値・構造を iPSC にそのまま転用しないことを明示する。主張は〔事実〕/〔推定〕/〔未確定〕でラベル付けした。*
