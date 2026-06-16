# ADR-0001: Control architecture — thin LLM orchestrator over deterministic tools + Bayesian optimization

- Status: **Accepted**（2026-06-14, decider: user）
- Context 前提: `../requirements.md`（R&D/プロセス開発・Human-on-the-loop）, `../kg_to_auto_cell.md` §4/§6/§7.2
- 関連 KG: `bbo`, `sdl`, `doe`, `loop`, `sched`, `orch`, `kanda`, `kinetics`/`src_manstein`

## Context

「現行 physical-ai-core の **ReAct ループ（毎周期 LLM が perceive→reason→act）＋ sanitizer ルール**が、auto_cell の
A 層制御に適切か」を要求仕様（C1–C7）で評価する課題。ユーザー方針: 「結局はパラメタ探索なのだから **ベイズ
最適化**でよしなに行けないか。**LLM は各種ツールを呼び、主要な制御はツール側**が行うべき」。

決定的な観察:
- R&D の中核価値は**条件探索/最適化**（FR-5）。これは LLM の自然言語推論より **BO（ガウス過程ベイズ最適化）**の
  領分。iPSC では先例あり（Kanda et al. 2022, GPyOpt バッチ BO; KG `bbo`/`kanda`）。
- run 内のプロセス制御は大部分が**既知レシピの決定的実行**（Manstein: 灌流 0→7 vvd・固定設定点・条件起動給餌;
  KG `kinetics`/`src_manstein`）＋局所 PID（§7.2）。LLM の per-cycle 推論は不要で、再現性(NFR-Rep)・安全(NFR-S)・
  コスト(NFR-C)に不利。

## Decision

**LLM を制御ループから外す。** 制御の重心を**決定的ツール＋BO**に置き、LLM は**イベント駆動の薄い
オーケストレータ／例外処理／HMI** に降格する。4 層構成:

| 層 | 主体 | 役割 | 性質 |
|---|---|---|---|
| **L0 デバイス局所** | PID / レシピ実行（device, LADS Function） | 温度/pH/DO/撹拌の高速安全ループ | 決定的・秒オーダ・検証済 |
| **L1 run 内 監督制御** | **決定的レシピ実行器＋ルールエンジン**（ツール） | 灌流/給餌/撹拌/サンプリング/継代要否を状態とレシピから判断、包絡線拘束 | 決定的・30s+/イベント |
| **L2 run 間 最適化** | **ベイズ最適化**（ツール, SDL meta-loop） | 次 run のパラメタ（設定点/灌流スケジュール/播種/撹拌）を提案、結果で事後更新 | アルゴリズム・run 単位 |
| **L3 オーケストレーション/判断/HMI** | **LLM（ツール呼び出し）** | ワークフロー dispatch、曖昧な知覚解釈、新規例外、研究者対話・承認仲介 | イベント駆動・非常駐 |

要点:
- **「主要制御はツール側」= L0/L1/L2 がアルゴリズムで動く。LLM(L3) は決定点・例外・HMI でのみ起動**（毎周期では
  ない）。happy path のワークフロー dispatch は決定的オーケストレータでも可で、LLM は判断/曖昧さの所だけ。
- **BO は run 間のパラメタ探索（FR-5）専用**。run 内のリアルタイム制御・安全（FR-1〜4, NFR-S）は L0/L1 が担う。
  「ベイズ最適化でよしなに」は最適化軸をカバーするが制御/安全は別レイヤ、を明確に分ける。
- physical-ai-core の資産（MQTT/WorldModel/plugin ABC/device_registry/**tool_schemas・tool_handlers**/sanitizer）は
  **再利用**。変えるのは「LLM が毎周期 reason する」中心性だけ → **ツールを厚く、LLM を薄く**。tool/sanitizer 機構は
  むしろこの形に向く。core は editable なので cognitive loop の常駐を外す改修を行う。

### BO の設計上の含意（「よしなに」の中身）

- **レジーム**: 評価は *少数・高コスト（多日 run）・ノイズあり*。→ **バッチ BO**（多バイオリアクタ並行）＋
  **制約付き/Safe BO**（CPP 包絡線を侵さない提案）＋**多忠実度(multi-fidelity)**（Tier2 Manstein ODE を安価な
  低忠実評価に使い実 run 前にスクリーニング, §6）。
- **目的関数**: run 毎のスカラ/多目的（収量×生存率×未分化マーカー、コスト重み; KG `qccrit`）。定義が前提条件。
- **ライブラリ**: BoTorch/Ax（制約・多忠実度・バッチに強い）を推奨。GPyOpt は iPSC 先例だが旧い。
- **Human-on-the-loop**: 包絡線を外れる BO 提案・継代等は**人の承認**へエスカレーション（FR-4）。L3-LLM が承認
  対話を仲介。

## 評価（C1–C7: 採用案 vs 現行 ReAct）

| 基準 | 採用案（L0-L3） | 現行 ReAct ループ |
|---|---|---|
| C1 権限分界 | ✓✓ LLM は高速/安全ループ外 | ✗ LLM が制御ループ内 |
| C2 再現/説明 | ✓✓ 決定的制御＋BO 事後分布は再現/可視 | ✗ LLM 非決定性 |
| C3 探索効率 | ✓✓ BO＋多忠実度 sim | △ LLM 推論は探索に非効率 |
| C4 縮退運転 | ✓✓ LLM 不在でも L0/L1/L2 継続 | ✗ LLM 依存 |
| C5 知能の必要量 | ✓✓ LLM 非常駐・判断時のみ | ✗ 毎周期 LLM（コスト/遅延） |
| C6 承認モデル | ✓ 包絡線外→承認、LLM が仲介 | △ |
| C7 保守/試験 | ✓ ツール単体試験＋Tier2 回帰、LLM 層が薄く検証少 | △ LLM 挙動の検証重い |

→ 採用案が C1/C2/C4/C5 で決定的に優位。ユーザー方針を支持。

## Consequences

- **physical-ai-core の ReAct cognitive loop（毎周期 LLM）は A 層制御の中心には使わない**。SOMS/auto_JA リネージの
  ReAct 常駐とはここで分岐する（core 資産は流用、cognitive loop の常駐のみ外す）。← 要 core 改修、リネージ文書に注記。
- **新規実装物**: 決定的レシピ実行器＋ルールエンジン(L1)、BO エンジン(L2, BoTorch/Ax, 制約・多忠実度・バッチ)、
  Tier2 sim を BO の低忠実度として接続。LLM は L3 の薄いオーケストレータ/HMI。
- **DomainVertical との対応**: tool_schemas/tool_handlers が L1/L2 の「ツール」面（set_perfusion_rate, trigger_passage,
  propose_next_run(BO) 等）、sanitizer/validate_tool_call が包絡線、build_summary/system_prompt が L3-HMI。
- **v1 では LLM はオプションでもよい**: L0/L1/L2＋決定的オーケストレータ＋HotL 承認で「包絡線内 SDL」は回る。
  LLM(L3) は HMI/例外/曖昧知覚の価値が要るときに足す（段階導入可）。

## Alternatives considered

- **① 現行 ReAct ループ常駐（却下）**: C1/C2/C4/C5 で劣後。R&D でも runtime は既知レシピ実行が大半で LLM 常駐は過剰。
- **② 完全決定的（BO＋ルール＋オーケストレータ, LLM なし）**: C1-C5 良好だが、曖昧知覚解釈・新規例外・自然言語
  HMI/研究者対話を失う。→ ③ の L3 を「オプション/段階導入」とすることで本質的に包含。
- **③ 採用案（L0-L3 ハイブリッド, LLM は薄い L3）**: ②を内包しつつ LLM 価値を端点に限定。採用。

## Follow-ups（要決定/実装, このADR外）

- 目的関数の具体定義（qccrit→スカラ/多目的）。
- BO ライブラリ確定（Ax/BoTorch）と探索空間/制約の定義 → ICD/devprofile の setpoint 包絡線と一体（§7.3）。
- L1 ルール/レシピの記述形式（state machine / recipe DSL）。
- core(physical-ai-core) の cognitive-loop 改修方針（常駐解除 or イベント駆動化）。

## 9. 将来制御層の位置づけ（MPC / PINN / デジタルツイン / 信頼度スコア）

> 本節は設計再検討（`design_reconsideration_report.md` §5.1 C1）に基づき、ADR-0001 の L0–L3 分離を維持しつつ将来技術を位置づける。〔設計判断〕

### 9.1 MPC を L1 の将来拡張として位置づける

- **v1 / Phase 1**: L1 は決定的レシピ/ルールエンジンのまま。MPC は導入しない。
- **Phase 2**: `sim/plant_model`（Manstein ODE）上で **MPC シミュレーション**を開始する。操作変数は perfusion rate、状態変数は VCD/glucose/lactate/osmolality 等。制約は CPP 包絡線（§4）と ramp 制限。〔`mpc`, `mpc_ipsc_perfusion`, `mpc_roadmap_l1`〕
- **Phase 3**: 30–100+ run 蓄積後、**多変数適応 MPC** を L1 拡張として実装する対象を検討。操作変数を perfusion rate・撹拌 rpm・DO setpoint 等へ拡大。〔`mpc_roadmap_l1`〕
- **根拠**: CHO fed-batch における MPC 実用化（抗体タイトル 2% 向上等）が報告されている。iPSC 灌流プロセスでも、特に **perfusion rate の制約付き最適化**（乳酸/osmolality 抑制）に有効な可能性がある〔`mpc_lactate_feedback`, `dynamic_perfusion_ipsc`; 推定〕。ただし iPSC への直接転用は実証が必要。〔`alignment_with_downloaded_report.md` §5.1-1〕

### 9.2 PINN / デジタルツイン / Hybrid ODE+NN を plant_model / L2 BO 低忠実度モデルの拡張として位置づける

- **Phase 1–2**: Tier2 plant_model は **Manstein 2021 ベースの 6 項 Monod ODE** を維持。これは CSV/CSA 検証リグとして決定的・再現可能である。〔`kinetics`, `src_manstein`; DOI 10.1002/sctm.20-0453, PMC8666714〕
- **Phase 2**: ODE の予測バイアスを GP 等で補正する **bias-correction surrogate** を L2 BO の低忠実度評価に導入。〔`multi_fidelity`, `bbo`〕
- **Phase 3**: 物理法則（ODE）とニューラルネットを組み合わせた **Hybrid ODE+NN** または **Physics-Informed Neural Network (PINN)** へ plant_model を拡張。デジタルツイン（DT）として sim/real gap を縮小し、L2 BO の低忠実度モデルとして活用する。〔`pinn`, `hybrid_ode_nn`, `digital_twin`, `multifidelity_pinn`〕
- **データ要件**: PINN/DT の構築には 50–100+ run 規模のデータが推奨される〔`data_requirement_pinn`; 推定〕。Phase 3 以降を想定。

### 9.3 信頼度スコア層を L2/L3 と HMI の間に追加

- **位置づけ**: `prediction_confidence_score` / `confidence_score` 層を L2/L3 と HMI の間に挿入する。〔設計判断〕
- **役割**:
  - L2 BO/GP 提案の GP 事後分散から信頼度を計算。
  - 将来 Raman PLS の Q 残差/Hotelling T² から信頼度を計算。
  - 将来画像 DL の予測不確実性（ensemble/MC dropout）から信頼度を計算。
  - 信頼度が閾値未満の場合、**自動的に HITL 承認へエスカレーション**する。
- **HMI 表示**: 各 AI/統計モデルの提案とともに信頼度スコア（例：0–1）とその根拠（GP 分散、使用された特徴量等）を表示する。〔`xai`, `feature_attribution`〕

### 9.4 将来技術は Human-on-the-loop 承認を必須とする

- MPC の実 run 導入（Phase 3 以降）、PINN/DT モデルの更新、Raman 閉ループ化（v2）、画像 DL 品質代理指標の運用化は、すべて**研究者/運用責任者の承認**を必須とする。〔`human_approval`, `approval_workflow`, `hitl`〕
- L3 LLM は現行設計どおり非クリティカル用途に限定し、setpoint 最終決定・安全インターロック上書き・無菌バリア無効化等のクリティカル用途には使用しない。〔`annex22`, `critical_ai`, `noncritical_ai`, `llm_orchestrator`〕

### 9.5 トレーサビリティ

| 設計要素 | KG ノード |
|---|---|
| MPC 将来拡張 | `mpc`, `mpc_ipsc_perfusion`, `mpc_roadmap_l1`, `mpc_lactate_feedback` |
| PINN/DT/Hybrid ODE+NN | `pinn`, `digital_twin`, `hybrid_ode_nn`, `multifidelity_pinn` |
| 信頼度スコア | `prediction_confidence_score`, `confidence_score` |
| HITL / 承認 | `human_approval`, `approval_workflow`, `hitl` |
| Annex 22 制約 | `annex22`, `critical_ai`, `noncritical_ai` |
