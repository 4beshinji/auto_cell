# S01: iPSC 浮遊灌流プロセスにおける MPC 適用調査レポート

> **Scope**: auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御、Manstein 型灌流 0→7 vvd）  
> **目的**: ADR-0001 で「将来の L1 拡張」に位置づけられた MPC を、iPSC 浮遊灌流プロセスにどう導入するかの実装計画に直接使える調査レポートを作成する。  
> **Date**: 2026-06-30  
> **前提文書**:
> - `docs/design/closed_loop_planning/01_roadmap_criticism_verification.md`
> - `docs/design/closed_loop_planning/02_missing_assets_for_closed_loop.md`
> - `docs/design/adr/0001-control-architecture.md`
> - `docs/design/kg_to_auto_cell.md`（§4 CPP, §7.2 制御権限分界）
> - `docs/design/ground_knowledge/additional_investigation_integrated.md` §2
> - `docs/design/ground_knowledge/additional_mpc_for_ipsc.md`

---

## Executive Summary

- **iPSC 浮遊凝集体灌流プロセスそのものの MPC 実証例は、査読付き論文・ベンダー事例ともに限定的**である〔事実〕。文献のほとんどは CHO fed-batch/perfusion または MSC・造血幹細胞培養が対象であり、iPSC 凝集体にそのまま転用できない。
- 一方、**MPC は灌流率を操作変数とする制約付き最適化の枠組みとして技術的に成立する**〔推定〕。状態変数は VCD・生存率・glucose/lactate/glutamine・浸透圧・凝集体径、操作変数は perfusion rate（＋必要に応じ bolus feed）、制約は CPP 包絡線・ramp 制限で定式化可能である。
- **実装ライブラリの推奨**: Phase 2 シミュレータは **CasADi + do-mpc**（Python、迅速なプロトタイピング）、将来の組み込み実装は **acados**（C コード生成・RTI）へ移行するのが現実的である。CVXPY/GEKKO は iPSC 灌流の遅い動態・少数 run という特性より、開発速度・物理モデル組み込みの観点で後手になる〔推定〕。
- **L1 ルールエンジンとの統合**: MPC は「上位監督 setpoint アドバイザー」として動作し、提案する setpoint 変化は `validate_tool_call` / sanitizer による包絡線検証を通過してから L1/デバイスへ出される。包絡線外・低信頼度・タイムアウト時は自律実行せず承認フローへエスカレーションする〔設計判断〕。
- **計算コスト・cadence**: iPSC 培養の応答は時間〜日スケールなので、MPC 求解時間は **数十秒〜数分**でも実用上問題ないケースが多い〔推定〕。Phase 2 では 30 min〜2 h の更新 cadence、Phase 3 でも分単位〜15 min 程度で十分である。
- **Human-on-the-loop**: 先行例として、バイオプロセス業界の MPC は「 supervisory setpoint 軌道を提示し、オペレータが確認してから下位 PID の setpoint を変更する」形が一般的である。auto_cell では `state/approval/{request_id}` topic を使い、**requested → approved/rejected/pending_timeout → executed/cancelled** の状態遷移を実装する〔設計判断〕。
- **Annex 22 下の位置づけ**: Critical 制御経路に置く場合、MPC は**静的・決定論的モデル**（固定 ODE + 固定制約、バージョン固定、再現性証明）として扱う。適応更新・確率的出力・生成 AI は Critical 用途にできない〔推定：Annex 22 草案〕。

---

## 1. 調査方法

- **WebSearch**: iPSC/PSC 浮遊灌流 + MPC、perfusion bioreactor MPC、CasADi/do-mpc/acados 比較、Human-in-the-loop/approval workflow、PIC/S Annex 22 AI 規制 について検索。
- **FetchURL**: 一次情報（PMCID 論文、DYCOPS 論文 PDF、do-mpc 公式ドキュメント、Bioprocess International 記事、Annex 22 解説）を取得。
- **前提文書レビュー**: ADR-0001、kg_to_auto_cell.md、additional_mpc_for_ipsc.md 等から設計制約・既存知見を抽出。
- **確度ラベル**: 各主張に以下のいずれかを付与。
  - **事実**: 一次情報または設計文書で確立されている。
  - **推定**: 文献・知見からの論理的推論だが iPSC 直接実証が不完全。
  - **未確定**: 現時点で実証・定量化が不十分。
  - **設計判断**: auto_cell 設計上の意思決定。

---

## 2. iPSC 浮遊灌流における MPC 実証例

### 2.1 直接実証例は限定的

| 対象 | 内容 | 出典 | 確度 |
|---|---|---|---|
| iPSC 浮遊凝集体灌流 | **査読付き MPC 実証論文は本調査で確認できなかった** | — | 未確定 |
| hiPSC 動的浮遊培養 | 灌流系の設計・拡大に関する報告はあるが、MPC 閉ループは確認できなかった | PMC10636629; SwRI 01-R6645 | 未確定 |
| 細胞治療（MSC・造血幹細胞） | 乳酸ベース適応 DARX-MPC。3 ドナー×6 戦略×3 反復で R² 99.80% ± 0.02%、未知トリプリケートで平均 96.57% の適合 | Van Beylen 2020, DOI 10.3390/bioengineering7030078 | 事実 |
| PSC 動的灌流 | pH 6.8 をトリガーに perfusion rate を 30%/日で ramp。固定灌流より day 6 で 25% 高密度化、乳酸 15 mM 未満抑制 | Huang 2020, DOI 10.18063/cgti.v1.i1.1784 | 事実 |
| Manstein 2021 | 7 日で 35×10⁶ cells/mL 達成。Berkeley-Madonna による in silico パラメータ最適化（灌流 1→2 vvd、glucose 3.15→7.65 g/L、80 rpm） | Manstein 2021, DOI 10.1002/sctm.20-0453; PMC8666714 | 事実 |

### 2.2 間接実証・隣接事例

- **CHO fed-batch/perfusion の MPC 実機例**が多数存在する。Rashedi et al. (DYCOPS-2022) は Amgen の fed-batch CHO で線形 MPC を実装し、最終タイトル 2% 向上、グルコース投与量 35% 増加、タンパク質純度改善を報告した〔事実：DYCOPS-2022 paper 0202〕。ただし、これらの改善率は **iPSC 製品（未分化マーカー維持・凝集体品質）には直接当てはまらない**〔事実〕。
- **Pappenreiter et al. 2022** は mAb perfusion の 30 日間定常運転を Monte-Carlo シミュレーションで評価し、single prediction control（MPC 系）が VCC・harvest flow の変動を半減し、30 日間で 4.5–10% の total product loss 削減が可能と報告した〔事実：PMC9399210〕。これは灌流率・bleed 率を操作変数とする制約付き制御の妥当性を示唆するが、対象は CHO/mAb である〔推定〕。
- **Sartorius-Stedim Data Analytics** の業界解説では、MPC は「regulatory layer（PID）の上の supervisory layer」として glucose setpoint 等の将来軌道を最適化する位置づけとされている〔事実：Bioprocess International 2017〕。

### 2.3 結論

iPSC 浮遊灌流の MPC 導入は、現時点では **直接実証に乏しく、CHO 等の隣接事例を参考にした段階的導入**が必要である〔推定〕。Phase 2 では `sim/plant_model`（Manstein ODE）を内部モデルとしたシミュレーション評価を優先し、実データでモデル適応後に閉ループ昇格させる〔設計判断〕。

---

## 3. 灌流率を操作変数とする制約付き最適化の定式化例

### 3.1 状態・操作変数・外乱・制約

A 層 iPSC 浮遊灌流（Manstein 型 0→7 vvd）を想定した NMPC 定式化案を以下に示す〔推定〕。

| 要素 | 候補 | 備考 |
|---|---|---|
| **状態 x** | VCD, viability, glucose, lactate, glutamine, osmolality, aggregate_diameter, DO, pH | glucose/lactate は Raman/Nova；VCD は capacitance；凝集体径は at-line 画像 |
| **操作変数 u** | Perfusion rate [vvd]（主レバー）; glucose/glutamine bolus feed [g or mL]（将来拡張） | 灌流が glucose 供給と lactate/osmolality 希釈を一手に握る〔事実：ADR-0001 §7.2〕 |
| **外乱 w** | 細胞株特異的成長率 µ、凝集体形成動態、温度ラボジット、Nova/Raman 校正誤差 | 適応更新または MHE で吸収（適応型は Annex 22 上の扱いに注意） |
| **硬制約 g(x,u)** | 0 ≤ perfusion ≤ 7 vvd; glucose > 1.5 mM; lactate < 50 mM; osmolality < 500 mOsm/kg; aggregate 150–350 µm; pump ramp ≤ 0.5 vvd/30 min | CPP 包絡線（Manstein 2021）〔事実：kg_to_auto_cell.md §4〕 |
| **軟制約** | lactate/osmolality 目標値違反のペナルティ、凝集体径の乖離ペナルティ | 制約違反を許容しつつ最小化 |
| **目的関数 J** | 多目的: VCD 目標軌道追従 + viability 維持 + 乳酸抑制 + 培地コスト + （将来）未分化マーカー維持 | 品質項は offline/run 単位で検証・重み調整が必要〔推定〕 |

### 3.2 典型的な目的関数形式

Rashedi et al. 2022 の線形 MPC と同様に、以下の二次形式が参考になる〔事実〕。

```
min J = Σ_{k=1}^{T_P} Σ_i W_i (X_i[t+k] - X_i^{ref}[t+k])²
        + Σ_{j=1}^{T_C} W_u (u[t+j-1] - u[t+j-2])²
```

- `T_P`: 予測ホライズン（例：6–24 h、最終的には 1–2 日）
- `T_C`: 制御ホライズン（例：1–6 h）
- `W_i`: 各状態の重み（VCD/lactate/osmolality/aggregate 等）
- `W_u`: 操作変化の抑制重み（ポンプ・シアショック回避）

iPSC 版では、**参照軌道 `X_ref` を Manstein 2021 の「7 日 35×10⁶ cells/mL」軌道に初期設定**し、実データで更新する〔設計判断〕。

### 3.3 灌流制御戦略の比較

| 戦略 | 操作変数 | フィードバック | 長所 | 短所 |
|---|---|---|---|---|
| 固定灌流 | time-based perfusion rate | なし | 単純・決定的 | 擾乱に弱い |
| ルールベース動的灌流 | pH/glucose/lactate トリガー + 固定 ramp | pH / daily metabolite | 実装容易 | 最適性・多変数対応が弱い |
| CSPR 制御 | perfusion rate = q × VCD | online biomass | 培地効率重視 | iPSC での q の定量化が未確定 |
| **MPC** | perfusion rate (+ feed bolus) | 多変数状態 + 予測モデル | 多変数・制約・将来報酬を統合 | モデル同定・検証コスト |

---

## 4. 実装ライブラリの比較

### 4.1 候補ライブラリの比較表

| ライブラリ | 言語 | 非線形対応 | リアルタイム/組み込み | 学習モデル統合 | 長所 | 短所 | auto_cell への適合 |
|---|---|---|---|---|---|---|---|
| **CasADi** | C++/Python | ◎ | 可（コード生成あり） | 可（PyTorch/ONNX 等の手動接続） | 記号的微分、NLP ソルバー（IPOPT）との親和性 | 低レベル、実装工数 | 内部モデル定義の基盤 |
| **do-mpc** | Python（CasADi 上） | ◎ | 中（研究〜プロトタイプ向け） | 可（NN/GP 例あり） | 迅速なプロトタイピング、MHE、不確実性対応、可視化 | 本番組み込みでは追加最適化が必要 | **Phase 2 推奨** |
| **acados** | C（Python/MATLAB インターフェース） | ◎ | ◎（RTI、組み込み向けコード生成） | 可（L4acados 等で外部感度） | HPIPM QP ソルバー、高速、μs〜ms オーダー | ワークフローが重い（コード生成・コンパイル） | **Phase 3 推奨** |
| **CVXPY** | Python | 凸のみ | 不可 | 不可 | 凸問題なら簡潔 | 非線形・動的制御には不向き | 不向き |
| **GEKKO** | Python | ◎ | 中（APMonitor エンジン） | 可 | 動的最適化が直感的 | クラウド/ブラックボックス感が強い、バイオプロセス実績は少ない | 補助的 |

### 4.2 iPSC 灌流（遅い動態・少数 run）に向く理由

- **遅い動態**: iPSC 培養の細胞成長・代謝応答は時間〜日スケール。MPC の求解時間が **数秒〜数分**でも、制御性能に支障をきたさない〔推定〕。したがって acados の「μs 級」性能は必須ではないが、将来的な multi-bioreactor 並列や実機組み込みを考慮すると acados 移行は理にかなう。
- **少数 run**: Phase 2 では 30 run 程度しかないため、**ハイブリッドモデル（物理 ODE + 少量データ補正）**が有効。do-mpc は CasADi 上で ODE 定義が容易であり、GP/NN 残差を組み込む例も存在する〔推定〕。
- **物理モデルの流用**: `sim/plant_model`（Manstein ODE）をそのまま内部モデルに使える。CasADi/do-mpc は ODE ベースのモデルを自然に扱う。

### 4.3 推奨ロードマップ

| フェーズ | 推奨スタック | 理由 |
|---|---|---|
| Phase 2（シミュレーション） | **do-mpc + CasADi + IPOPT** | Python 上で迅速に NMPC/MHE を構築し、`sim/plant_model` との整合を検証 |
| Phase 2 後半〜Phase 3 | **acados**（必要に応じて L4acados） | C コード生成で実機性能・RTI を確保。感度計算を外部化して GP/NN 残差を組み込み |
| Phase 3 経済 MPC | acados + CasADi 前処理 | 長期ホライズン（1–2 日）の経済目的関数も求解可能 |

---

## 5. MPC と L1 ルールエンジンの統合パターン

### 5.1 統合コンセプト

MPC は **L1 決定的ルールエンジンの「上位 setpoint アドバイザー」**として配置する〔設計判断〕。L0 デバイス局所 PID はそのまま維持し、MPC は L1 の「推論された setpoint 変化候補」を提案する。

```
L0: 局所 PID（pH/DO/温度/撹拌）
  ↑ setpoint
L1: 決定的レシピ/ルールエンジン + sanitizer
  ↑ setpoint trajectory 提案
L2-MPC: 多変数予測最適化（perfusion rate, feed bolus, agitation setpoint）
  ↑ 承認
L3/HMI: Human-on-the-loop 承認・監査・異常時介入
```

### 5.2 包絡線検証フロー

MPC が提案する操作変化は、必ず `validate_tool_call` / sanitizer を通過させる〔設計判断〕。

| ステップ | 処理 | 実装箇所 |
|---|---|---|
| 1. MPC 求解 | 現在状態から最適操作系列 `u*(t..t+T_C)` を計算 | `src/auto_cell/plugins/cell_culture/mpc_advisor.py`（新設） |
| 2. 包絡線検証 | 各ステップの u が CPP 包絡線（0–7 vvd、ramp ≤ 0.5 vvd/30 min 等）を満たすか検証 | `sanitizer.py` / `validate_tool_call` |
| 3. 信頼度評価 | モデル予測不確実性（GP 事後分散、MHE 残差、制約活性度）から信頼度スコアを計算 | `confidence.py` |
| 4. 承認判定 | 包絡線内かつ高信頼度なら自動実行、それ以外は HMI 承認要求 | `state/approval/{request_id}` topic |
| 5. 実行 | 承認済みの先頭操作 `u*(t)` を L1/デバイスへ送信 | `tool_handlers` / MQTT cmd/ack |
| 6. 監査ログ | 提案軌道・検証結果・承認履歴・実行結果を event_store へ記録 | `audit_log` |

### 5.3 提案軌道の提示項目

HMI 承認画面には以下を表示する〔設計判断〕。

- 予測ホライズン内の状態軌道（VCD、glucose、lactate、osmolality、aggregate diameter）
- 提案操作系列（perfusion rate、feed bolus、agitation setpoint）
- 各時点での制約とのマージン
- 信頼度スコアと根拠（例：「GP 事後分散 0.02、MHE 残差 3%」）
- 既存レシピ軌道との差分

---

## 6. 計算コストと cadence

### 6.1 先行例の求解時間

| 事例 | スケール | 求解時間 | サンプリング時間 | 出典 |
|---|---|---|---|---|
| 倒立振子 NMPC（ACADO） | 小規模 | **80 μs** / RTI step | 50 ms | Quirynen 2014, Autogenerating Microsecond Solvers |
| 6 軸ドローン（acados） | 中規模 | 平均 2 ms、最大 7 ms | 10 ms | acados forum 2024 |
| 自動車回避（ACADO） | 中規模 | 90 ms 以下 | — | core.ac.uk 2019 |
| バイオリアクタ cost-to-go MPC | 小〜中規模 | 古典 MPC 0.1 s、cost-to-go MPC **12 s**（最大 17 s） | 18 s | Markler 2024, TU Wien thesis |
| バイオリアクタ MPC（MATLAB） | 小規模 | 0.1737 s | 1 s | semantic scholar 論文 |
| バイオリアクタ MPC（acados） | 中規模 | 50–60 ms（warm-up 後） | — | infovaya 資料 |

### 6.2 iPSC 培養に必要な cadence

iPSC 浮遊灌流では以下の時間スケールが支配的である〔推定〕。

| プロセス動態 | 時定数/応答時間 | MPC の扱い |
|---|---|---|
| VCD 増殖 | 半減期〜12 h、目標達成まで数日 | 予測ホライズン 6–48 h |
| glucose/lactate 変動 | 給餌・灌流で 30 min〜数 h | 制御ホライズン 30 min〜2 h |
| 浸透圧変動 | 灌流・交換で 1–6 h | 状態制約で扱う |
| 凝集体径変化 | 撹拌・成長で 1–12 h | 間接的状態制約 |
| DO/pH/温度 | 秒〜分（L0 PID で処理） | MPC では setpoint 変更のみ |

**結論**: iPSC 灌流 MPC では、**求解時間が数十秒〜数分、更新 cadence が 15 min〜2 h**で十分実用的である〔推定〕。solver timeout は 5 min、通常 cadence は 30 min 程度から開始し、実データで調整する〔設計判断〕。

### 6.3 タイムアウト・デッドラインミス対策

- **solver timeout**: 設定時間内に収束しなかった場合、最後の実行可能解を採用、または安全側のデフォルト灌流率を維持する〔設計判断〕。
- **deadline miss**: 次の制御周期が来ても求解が終わっていない場合、前回の制御入力をホールドし、HMI に警告を通知する。
- **warm-up**: acados では初回実行に時間がかかるため、プロセス開始前にダミー状態で 1 回 warm-up 実行する〔推定〕。

---

## 7. Human-on-the-loop：承認フロー・タイムアウト設計

### 7.1 先行例

- **バイオプロセス業界の MPC**: ほとんどが「supervisory setpoint/trajectory を提示し、オペレータが承認・調整してから下位 PID setpoint を変更」する形で運用されている〔事実：Bioprocess International 2017〕。
- **汎用 HITL ワークフロー**: 重要操作の前に人間承認を挟み、タイムアウトで自動エスカレーションまたはキャンセルするパターンが一般的〔事実：Temporal チュートリアル、StackAI 記事〕。
- **auto_cell 設計**: `state/approval/{request_id}` topic と `notify/hmi/{priority}` topic を使い、承認状態を管理する〔事実：kg_to_auto_cell.md §7.3〕。

### 7.2 推奨承認フロー

| トリガー | 承認要否 | タイムアウト | タイムアウト時のデフォルト |
|---|---|---|---|
| MPC 提案が包絡線内・高信頼度 | 不要（自動実行） | — | — |
| MPC 提案が包絡線内だが低信頼度 | 要 | 10 min | 前回値ホールド |
| MPC 提案が包絡線外 | 要 | 10 min | 提案キャンセル（安全側 setpoint 維持） |
| MPC 提案に agitation setpoint 変更を含む | 要 | 10 min | キャンセル |
| trigger_passage / 継代 | 要 | 30 min | キャンセル＋ホールド |
| MPC solver timeout / 異常 | 即時通知 | — | 安全側 setpoint 維持 |

状態遷移は `requested → approved | rejected | pending_timeout → executed | cancelled` とする〔事実：kg_to_auto_cell.md §7.3〕。

### 7.3 承認画面の必須情報

- 提案理由（目的関数の改善量、例：「予測 VCD 終点 +5%」）
- 予測軌道グラフ（状態・操作変数）
- 制約マージン表
- 信頼度スコアと根拠
- 既存レシピからの差分
- 「承認」「一部修正」「拒否」「ホールド」ボタン

---

## 8. Annex 22 下での位置づけと検証戦略

### 8.1 Annex 22 の主要制限

PIC/S Annex 22（2025-07-07 草案）によれば、Critical GMP 用途では以下が要求される〔事実：EC/PIC/S consultation guideline; pharmout.net; regask.com〕。

| 許容 | 禁止（Critical 用途） |
|---|---|
| 静的モデル（static model） | 動的モデル（dynamic/continuously learning） |
| 決定論的出力（deterministic output） | 確率的出力（probabilistic output） |
| 明示的ルール・状態機械 | 生成 AI / LLM |

### 8.2 MPC の分類可能性

| MPC 実装形態 | Annex 22 分類 | 備考 |
|---|---|---|
| **固定 ODE ベース NMPC**（Manstein ODE、パラメータ固定、バージョン固定、再現性証明あり） | 静的・決定論的モデルとして扱える可能性 | Critical 制御経路に配置可能〔推定〕 |
| **線形 MPC（LMPC）**（固定線形モデル） | 静的・決定論的 | 最も規制リスクが低い〔推定〕 |
| **適応 MPC / MHE パラメータ更新** | 動的モデル扱い → Critical 用途不可 | アドバイザリ/非クリティカルに限定〔推定〕 |
| **NN/PINN 残差を含む MPC** | モデル構造・訓練データ・バージョン固定であれば議論可能 | 黒箱部分の explainability・静的証明が課題〔推定〕 |
| **確率的 MPC / サンプリングベース MPC** | 確率的出力 → Critical 用途不可 | 非クリティカル/研究用途のみ〔推定〕 |

### 8.3 Critical 制御経路に MPC を置く場合の検証戦略

MPC を L1 の Critical 経路に組み込む場合、以下の技術的統制が必要である〔推定：Annex 22 解説を踏まえた設計判断〕。

1. **モデルの静的固定**
   - 内部モデル（Manstein ODE + 必要なら固定補正項）をバージョン管理。
   - 訓練データ・パラメータ・ソルバー設定を checksum 化し、運用時に変更不可とする。
2. **決定論的出力の証明**
   - 固定シード・固定初期状態・固定モデルで同一の入力に対し同一の制御出力を生成することを CI で検証。
   - `tests/test_mpc_determinism.py` のような回帰テストを作成。
3. **データ分離**
   - モデル同定用データ（train/valid）と性能評価用データ（test）をリポジトリ分離。
   - 運用データは test セットに混入させない。
4. **Explainability**
   - 各時点での予測軌道・活性制約・目的関数項の寄与を可視化。
   - SHAP 等は非線形残差モデルに適用可能。
5. **信頼度スコア**
   - GP 事後分散 / MHE 残差 / 制約活性度から信頼度を計算。
   - 閾値未満は HITL エスカレーション。
6. **性能等価性**
   - 既存の L1 決定的ルールベース制御との side-by-side 比較を実施。
   - 指標：VCD 軌道追従誤差、lactate/osmolality 制約違反回数、培地消費量、生存率、未分化マーカー陽性率。
7. **職員独立性・dual control**
   - モデル開発者と検証者を分離。
   - 承認者は別の訓練を受けた研究者/オペレータとする。

### 8.4 段階的な規制対応

| フェーズ | MPC の位置づけ | Annex 22 対応 |
|---|---|---|
| Phase 1 | 導入なし（L1 決定的ルール） | 該当なし |
| Phase 2 | **シミュレーション評価**（`sim/plant_model` 上） | 研究開発用途。静的決定論的実装の設計・検証を並行実施。 |
| Phase 3 初期 | **アドバイザリ MPC**（HMI 提示・人承認後に L1 反映） | 非クリティカル用途として扱いつつ、HITL ログを蓄積。 |
| Phase 3 後期 | **Critical L1 拡張 MPC**（自動実行） | 上記 8.3 の検証戦略を完了後に移行。 |

---

## 9. auto_cell への統合方針

### 9.1 モジュール構成（推奨）

```
src/auto_cell/plugins/cell_culture/
├── mpc_advisor.py          # MPC ソルバー呼び出し・軌道生成
├── mpc_model.py            # Manstein ODE → CasADi/do-mpc モデル
├── mpc_constraints.py      # CPP 包絡線・ramp 制限の定義
├── mpc_objective.py        # 目的関数・重み
├── mpc_confidence.py       # 予測信頼度スコア
└── mpc_hmi.py              # 提案軌道の HMI 表示用ペイロード生成

sim/plant_model/
├── __init__.py             # 既存 Manstein ODE
└── mpc_wrapper.py          # plant_model を MPC 内部モデルとして利用

tests/
├── test_mpc_determinism.py
├── test_mpc_envelope.py
└── test_mpc_happy_path.py
```

### 9.2 Phase 2（12–24 ヶ月）の実装スコープ

- **内部モデル**: `sim/plant_model`（Manstein ODE）を do-mpc モデル化。
- **単一操作変数 MPC**: perfusion rate のみを最適化。
- **目的関数**: VCD 軌道追従 + lactate 抑制 + 培地コスト。
- **制約**: CPP 包絡線 + pump ramp 制限。
- **HITL**: MPC 提案軌道を HMI で提示し、人承認後に L1 へ反映。
- **検証**: 決定性テスト、包絡線テスト、Manstein 軌道再現テスト。

### 9.3 Phase 3（24–48 ヶ月）の実装スコープ

- **多変数 MPC**: perfusion rate + glucose/glutamine bolus feed + agitation setpoint。
- **適応要素**: Raman/Nova/capacitance からのパラメータ更新（ただし Critical 自動実行には制限）。
- **経済 MPC**: 培地コスト・培養時間を目的関数に統合。
- **acados 移行**: 実機性能・RTI を確保。
- **規制文書化**: Intended Use、モデルカード、静的決定論的証明、性能等価性レポート。

### 9.4 MQTT topic 統合

既存の `cmd/ack` + `state/approval/{request_id}` + `notify/hmi/{priority}` topic 設計を流用する〔事実：kg_to_auto_cell.md §7.3〕。

| topic | 用途 | payload 例 |
|---|---|---|
| `cell/{cu}/mpc/proposal/{request_id}` | MPC 提案軌道発行 | `{trajectory, constraints, confidence, requested_by, timestamp}` |
| `cell/{cu}/state/approval/{request_id}` | 承認状態遷移 | `{state, approved_by, timestamp}` |
| `cell/{cu}/cmd/{device}/set_perfusion_rate` | 承認済み制御実行 | `{value, correlation_id, timestamp}` |
| `cell/{cu}/notify/hmi/P2` | 承認要求通知 | `{message, priority, request_id}` |

---

## 10. リスク・未確定事項

| # | リスク/未確定事項 | 影響 | 対応策 | 確度 |
|---|---|---|---|---|
| R1 | iPSC 凝集体特有の動的モデル（凝集体形成・シア応答）が未整備 | MPC 予測精度低下 | Phase 2 で Manstein ODE をベースに、実データで適応 | 推定 |
| R2 | Raman ベース in-line glucose/lactate の iPSC 校正精度が未確定 | 状態推定の質 | Nova FLEX2 を正解ラベルとした校正を先行 | 未確定 |
| R3 | MPC 目的関数の重み（収量 vs 品質 vs コスト）が未決定 | 最適化方向性のずれ | 研究者ヒアリング + 感度分析 | 推定 |
| R4 | 適応 MPC を Annex 22 Critical 用途にできない | 設計制約 | 適応要素はアドバイザリ/非クリティカルに限定、Critical 自動実行は固定モデルのみ | 推定 |
| R5 | 求解時間が予想より長大化（非収束） | 制御周期遅延 | solver timeout・前回値ホールド・HMI 警告 | 推定 |
| R6 | 細胞保持デバイス（ATF/TFF/重力沈降）の動的応答が未考慮 | 灌流率上限の誤設定 | デバイス特性を制約に追加（Phase 3） | 未確定 |
| R7 | 品質項（OCT4/SOX2/NANOG）が offline/run 単位 | run 内 MPC の品質最適化が困難 | offline 結果を Phase 3 経済 MPC の制約/項に統合 | 推定 |
| R8 | 少数 run（30 前後）でのモデル同定精度 | 過学習・外挿性能低下 | GP バイアス補正・Hybrid ODE+NN を段階導入 | 推定 |

---

## 11. 出典リスト

| ID | タイトル | 出典 | 確度関連 |
|---|---|---|---|
| Manstein 2021 | High density bioprocessing of hPSCs | DOI 10.1002/sctm.20-0453; PMID 33660952; PMC8666714 | 事実 |
| Huang 2020 | Process development and scale-up of PSC manufacturing | DOI 10.18063/cgti.v1.i1.1784 | 事実 |
| Van Beylen 2020 | Lactate-Based MPC Strategy of Cell Growth for Cell Therapy | DOI 10.3390/bioengineering7030078 | 事実 |
| Rashedi 2022 | Model Predictive Controller Design for Bioprocesses Based On Machine Learning Algorithms | DYCOPS-2022 paper 0202; https://skoge.folk.ntnu.no/prost/proceedings/dycops-2022/files/0202.pdf | 事実 |
| Pappenreiter 2022 | Predictive control of biomass in a perfusion bioreactor | PMCID PMC9399210; DOI 10.1186/s12934-022-01772-0 | 事実 |
| Bioprocess Intl 2017 | Model Predictive Control for Bioprocess Forecasting and Optimization | https://www.bioprocessintl.com/process-monitoring-and-controls/model-predictive-control-for-bioprocess-forecasting-and-optimization | 事実 |
| do-mpc docs | Batch Bioreactor example | https://www.do-mpc.com/en/latest/example_gallery/batch_reactor.html | 事実 |
| CasADi paper | CasADi – A Software Framework for Nonlinear Optimization and Optimal Control | DOI 10.1007/s12532-018-0139-4 | 事実 |
| acados paper | acados: A Modular Open-Source Framework for Fast Embedded Optimal Control | DOI 10.1007/s12532-022-00230-6; arXiv 1910.13753 | 事実 |
| L4acados 2024 | Learning-based models for acados | arXiv 2411.19258 | 事実 |
| Quirynen 2014 | Autogenerating Microsecond Solvers for Nonlinear MPC | DOI 10.1002/nme.4665 | 事実 |
| Markler 2024 | Cost-to-Go Model Predictive Control for Enhanced Bioprocesses | TU Wien thesis; https://repositum.tuwien.at/bitstream/20.500.12708/193908/1/Markler%20Christoph%20-%202024%20-%20Cost-to-Go%20model%20predictive%20control%20for%20enhanced...pdf | 事実 |
| PIC/S Annex 22 draft | EudraLex Volume 4 — Draft Annex 22: AI (July 2025) | https://health.ec.europa.eu/consultations/stakeholders-consultation-eudralex-volume-4-good-manufacturing-practice-guidelines-chapter-4-annex_en | 事実 |
| pharmout.net | Annex 22: The Rise of Artificial Intelligence | https://www.pharmout.net/annex-22-artificial-intelligence/ | 推定 |
| regask.com | Decoding the New PIC/S Annex 22 for Regulatory Teams | https://regask.com/ai-gmp-decoding-new-pics-annex-22-regulatory-teams/ | 推定 |
| intuitionlabs.ai | EU GMP Annex 22: AI Compliance in Pharma Manufacturing | https://intuitionlabs.ai/articles/eu-gmp-annex-22-ai-compliance-pharma | 推定 |
| ABB APC biopharma | Advanced process control in biopharmaceutical production | https://new.abb.com/control-systems/industry-specific-solutions/pharmaceutical-and-life-sciences/apc-mpc-model-predictive-control-for-biopharmaceutical | 事実 |
| StackAI 2026 | Human-in-the-Loop AI Agents: Approval Workflows | https://www.stackai.com/insights/human-in-the-loop-ai-agents-how-to-design-approval-workflows-for-safe-and-scalable-automation | 事実 |
| Temporal 2025 | Adding Durable Human-in-the-Loop to Our Research Application | https://learn.temporal.io/tutorials/ai/building-durable-ai-applications/human-in-the-loop/ | 事実 |
| bioprocesstools.com | Bioprocess Automation Guide: PID, SCADA, MPC and Digital Twins | https://bioprocesstools.com/blog/bioprocess-automation/ | 推定 |

---

*本レポートは CHO/mAb 由来の数値を iPSC にそのまま転用しないことを原則とし、実装計画に直接使える具体性を目指して作成した。主張は「事実 / 推定 / 未確定 / 設計判断」のラベル付きで記載している。*
