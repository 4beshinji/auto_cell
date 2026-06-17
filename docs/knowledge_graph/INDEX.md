# iPS 自動培養ソフトウェア ナレッジグラフ INDEX

> 本書は `knowledge_graph_v2_1.json` から生成した **人が読むための目次・カタログ** です。
> 対話的なグラフ表示は [`ips_automation_knowledge_map_v2_1.html`](ips_automation_knowledge_map_v2_1.html) をブラウザで開いてください。
> 設計への落とし込みは [`../design/kg_to_auto_cell.md`](../design/kg_to_auto_cell.md) を参照。

- **バージョン**: v2.1  
- **規模**: 340 ノード / 692 エッジ / 99 情報源  
- **生成日**: 2026-06-16  

## クイックリンク

| ビューア | データ正本 | 設計ブリッジ |
|---|---|---|
| [対話グラフ `ips_automation_knowledge_map_v2_1.html`](ips_automation_knowledge_map_v2_1.html) | [`knowledge_graph_v2_1.json`](knowledge_graph_v2_1.json) | [`docs/design/kg_to_auto_cell.md`](../design/kg_to_auto_cell.md) |
| [旧 v2 グラフ](ips_automation_knowledge_map_v2.html) | [`knowledge_graph_v2.json`](knowledge_graph_v2.json) | [`docs/design/adr/0001-control-architecture.md`](../design/adr/0001-control-architecture.md) |

## ドメイン別インデックス

### 細胞生物学・培養プロトコル (`d1`)

自動化の対象そのもの。iPS 細胞の樹立・維持・継代・分化誘導・量産の生物学的手順群で、各操作のパラメータが下流の制御変数になる。

**31 ノード** — 概念 19 / システム 0 / プレイヤー 0 / 情報源 12

<details>
<summary>主要概念 (19件)</summary>

| ラベル | 内容 |
|---|---|
| `add_cho_ipsc_cho_metabolism` CHO 代謝プロファイル | ハムスター卵巢由来 CHO 細胞の代謝特性。高グルコース消費、活発な乳酸産生、グルタミン分解によるアンモニア蓄積、mAb タイトル最大化が最適化目標。iPSC にはそのまま転用不可。 |
| `kinetic_cell_model` Kinetic Cell Model | Sub-model describing cell metabolism and growth kinetics. In advanced DTs it combines genome-scale metabolic networks... |
| `y_27632` Y-27632 ROCK inhibitor | Standard ROCK inhibitor added during dissociation passage to improve iPSC survival. |
| `add_cho_ipsc_glycolytic_shift` iPSC の高解糖性シフト | iPSC が未分化状態で解糖系を優位に使う代謝特性。高密度培養ではグルコース供給と乳酸洗浄のトレードオフが顕在化し、灌流制御の中核となる。 |
| `add_cho_ipsc_ipsc_metabolism` iPSC 代謝プロファイル | ヒト多能性幹細胞 iPSC の代謝特性。highly glycolytic で高密度化に伴いグルコース消費と乳酸分泌が急増。乳酸蓄積・浸透圧ピーク・凝集体サイズが成長制限因子。多能性維持が品質目標。 |
| `dynamic_perfusion_ipsc` iPSC 動的灌流戦略 | pH トリガー等で perfusion rate を動的に増加させる iPSC 浮遊培養戦略。Huang et al. 2020 で pH 6.8 トリガー + 30%/日増加により固定灌流比 25% 向上。MPC で多変数化・最適化可能。 |
| `add_cho_ipsc_qc_marker_panel` iPSC 多能性 QC マーカーパネル | iPSC の未分化性を評価するマーカー群。核内転写因子 OCT4/SOX2/NANOG、細胞表面マーカー SSEA-3/SSEA-4/TRA-1-60/TRA-1-81、核型/同一性。offline/run 単位で測定。 |
| `reprog` iPSC樹立（初期化） | 体細胞をRNA等で初期化しコロニーを得る最難関工程。形態が動的で良質コロニー選抜が職人技。財団・パナソニックが2026年に樹立工程の自動化実証に着手。 |
| `maint` iPSC維持培養 | 未分化状態を保つ日々の培地交換と環境維持。ヒトiPSは毎日の培地交換と約3日ごとの継代が必要で、熟練手技に依存する点が自動化の主対象。 |
| `signal` シグナル制御（添加因子） | 分化方向を決める阻害剤の濃度・タイミング。RPE誘導では FGFR阻害剤・SB431542(TGFβ)・CKI-7(Wnt)・Y-27632 等が制御変数。これらが最適化の探索空間になる。 |
| `feeder` フィーダーフリー培養 | フィーダー細胞を用いず基質コート上で培養する方式。臨床・自動化に適し、画像解析でも背景が単純化しやすい。 |
| `add_cho_ipsc_aggregate_oxygen_diffusion` 凝集体内酸素拡散限界 | iPSC 凝集体では径が大きくなると中心部への酸素/栄養拡散が制限され壊死コアが形成。100–200 µm の拡散距離、300 µm 以下の径制御が目安。 |
| `aggregate_formation_model` 凝集体形成動力学モデル | 凝集体の形成・合体・破砕を表す動的サブモデル。撹拌速度・細胞密度と凝集体径の関係を追加する拡張。 |
| `add_aggimg_aggregate_size_pluripotency` 凝集体径と多能性維持 | 凝集体径が大きくなると拡散制限により内部の酸素/栄養濃度が低下し、未分化性マーカー（OCT4 等）が低下・壊死が増大する。Borys 2021 では >400 µm で壊死リスク。細胞株・培地による変動あり。 |
| `diff` 分化誘導プロトコル | 目的細胞へ誘導する多段階手順。iPSC→RPEは seeding / preconditioning / passage / induction / maintenance の5段階として定式化され、自動探索のテンプレになった。 |
| `suspension` 浮遊・懸濁培養（量産） | 3次元浮遊撹拌で容積当たり密度を上げ量産する方式。突発的分化を化合物で抑制し、樹立→大量培養→直接凍結まで一貫化。自動化・スケールアップの基盤形態。 |
| `kinetics` 浮遊培養速度論モデル（Tier2 plant 原典） | iPSC浮遊培養の比増殖速度をMonod型で表すin silicoモデル。auto_cell Tier2 plant_modelの原典はManstein & Zweigerdt 2021（SCTM/STAR Protocols, sr... |
| `qccrit` 細胞品質基準 | 未分化マーカー発現・三胚葉分化能・核型など、製造物が満たすべき生物学的基準。自動判定の「正解ラベル」を定義し、画像代理指標と紐づける必要がある。 |
| `passage` 継代（剥離・分散） | コロニーを剥離し新プレートへ植え継ぐ工程。単一細胞分散かクランプ維持か、ROCK阻害剤(Y-27632)添加、シェアストレス管理が品質を左右する。 |

</details>

### 画像取得・コンピュータビジョン (`d2`)

ラベルフリー画像から細胞状態を定量し、意思決定の入力を生成する層。コンフルエンシー・形態・分化の判定が中核。

**19 ノード** — 概念 10 / システム 0 / プレイヤー 0 / 情報源 9

<details>
<summary>主要概念 (10件)</summary>

| ラベル | 内容 |
|---|---|
| `add_aggimg_2d_to_aggregate_transfer` 2D 画像解析→凝集体解析転移 | 2D confluency は浮遊凝集体に不適用。コロニー形態分類・分化領域検出・増殖曲線予測の技術スタックは転移可能だが、教師ラベルと特徴量を凝集体の径・形態・内部構造に読み替える必要がある。 |
| `add_aggimg_dl_morphology_pluripotency` DL 形態から多能性予測 | 明視野/位相差画像から CNN/U-Net/DenseNet 等で未分化/自発分化を予測する技術。2D コロニー・organoid で実証多数。iPSC 浮遊凝集体への転移は有望だが、教師データ・細胞株汎化が未解決。 |
| `dlmodel` DLモデル（分割/分類） | セグメンテーション(面積/コンフルエンシー)と分類(形態・分化)の学習モデル群。ラベルフリー前提・低コントラスト対応・施設間汎化が実装課題。 |
| `morphcls` コロニー形態分類 | 良/不良フェノタイプをCNN等で識別。形態パラメータが未分化性・クローン性維持能と相関し、選抜・除外の自動判断に使う。 |
| `conf` コンフルエンシー算出 | セグメンテーションで占有面積/コロニー面積を定量。継代や次工程移行の判断指標（例: 70-80%）として閾値化される中核メトリクス。 |
| `add_aggimg_aggregate_quality_proxy` 凝集体品質代理指標 | 凝集体画像特徴量（径分布、円形度、内部輝度勾配、輪郭粗さ等）から OCT4/SOX2/NANOG/SSEA4/TRA-1-60 等の offline 品質マーカーを推定する代理指標。v1 では未導入、v2 以降の DL 化候補。 |
| `diffdet` 分化領域検出 | 未分化コロニー内の自発分化領域を検出・定量。分化率の閾値超過ウェルを除外したり、誘導の進行度評価に用いる専用DLモデル。 |
| `growth` 増殖曲線予測→継代トリガ | 定期観察から面積値の増殖曲線を推定し、目標密度到達の至適時刻を予測。これがスケジューラと継代操作のトリガになる閉ループの起点。 |
| `bf` 明視野/位相差イメージング | 低光毒性で非侵襲なラベルフリー観察。一方で低コントラスト・不均一背景・ハロー/エッジ効果があり、頑健なセグメンテーションが難所。 |
| `add_aggimg_aggregate_imaging_survey` 浮遊凝集体画像解析調査 | iPSC 浮遊/凝集体の径・形態を at-line/in-line で計測し、label-free DL で品質代理指標を推定する技術群。v1 では at-line 明視野/位相差画像を主軸とし、DHM/FBRM/FlowCam はオ... |

</details>

### ロボティクス・液体ハンドリング (`d3`)

培養操作を物理的に実行する装置・ロボット層。汎用双腕と閉鎖型専用機の二系統がある。

**5 ノード** — 概念 5 / システム 0 / プレイヤー 0 / 情報源 0

<details>
<summary>主要概念 (5件)</summary>

| ラベル | 内容 |
|---|---|
| `transport` プレート搬送・把持 | インキュベータ⇄顕微鏡⇄作業台間のプレート/容器搬送とグリッパ制御。スケジュールに沿う物流が自律運転の連続性を支える。 |
| `dualarm` 双腕ヒューマノイド | 汎用器具をそのまま扱える人型双腕（例: LabDroid Maholo）。プロトコル変更に柔軟で、パラメータ探索や手作業の写像に向く。 |
| `motioncap` 熟練手技のモーション再現 | 熟練者の作業を動作解析し数値化してロボットで再現する思想。「誰でもできるよう数値化して自動化」が財団の自動化方針の核。 |
| `dispense` 自動分注・ピペッティング | 培地・試薬の精密分注と吸引。液面追従・体積制御・無菌チップ運用が再現性を決める。リキッドハンドラ統合の基本ユニット。 |
| `closeddev` 閉鎖型専用培養装置 | 装置内で取り出さず培養するクローズド機。無菌性・更衣簡略化・人為ミス低減に優れ、財団のmy iPS製造の中核アーキテクチャ。 |

</details>

### プロセス制御・自律最適化 (`d4`)

観察→判断→操作の閉ループと、プロトコル最適化（ベイズ最適化等）を担う制御知能の層。L0–L3 アーキテクチャ、MPC、BO、Human-on-the-loop が集約される。

**105 ノード** — 概念 80 / システム 2 / プレイヤー 0 / 情報源 23

<details>
<summary>主要概念 (80件)</summary>

| ラベル | 内容 |
|---|---|
| `bayesian_pinn` Bayesian PINN (B-PINN) | Variational inference over PINN weights to produce posterior predictive distributions. Theoretically grounded but com... |
| `add_cho_ipsc_mab_titer_objective` CHO の mAb タイトル目的関数 | CHO fed-batch/perfusion の最適化目標。抗体タイトル（g/L）、viable cell density × specific productivity、糖鎖パターン（CQA）。iPSC 目的関数とは本質的に異なる。 |
| `raman_cho_to_ipsc_transfer` CHO→iPSC Raman モデル転移制限 | CHO/mAb 由来の chemometric モデルを iPSC 浮遊凝集体に直接転用できない制約。培地マトリックス、代謝プロファイル、細胞サイズ/凝集体構造、品質指標が異なる。クローン間・スケール間転移すら補正を要する事例が報告さ... |
| `add_cho_ipsc_transfer_caution` CHO→iPSC 知見転用注意 | CHO 由来の CPP 数値・制御戦略・目的関数を iPSC にそのまま転用しないこと。細胞種・培地・反応器形状・製品特性（mAb vs 細胞製品）の違いを再解釈。 |
| `cobrapy_gem` COBRApy + GEM 差替候補 | 将来のゲノム規模代謝モデル（COBRApy）への差替候補。培地組成を制約ベースで解き、代謝物収支を予測。 |
| `add_cho_ipsc_cpp_reinterpretation` CPP の iPSC 再解釈 | CHO/mAb 中心の調査レポートから得られた知見を、iPSC 浮遊/凝集体灌流の文脈に再解釈する設計活動。L1 レシピ、L2 BO、L3 HMI に反映。 |
| `cpp_agitation` CPP: agitation rpm | A-layer agitation 50-120 rpm; Borys 2021 optimum 40-60 rpm for Vertical-Wheel iPSC. |
| `cpp_perfusion_rate` CPP: perfusion rate | A-layer main actuator 0->7 vvd (Manstein 2021 Table 3); conditionally triggered by glucose/lactate/osmolality. |
| `cpsr_control` Cell-Specific Perfusion Rate 制御 | 生存細胞数あたりの灌流率（CSPR）を一定に保つ制御戦略。培地利用効率と安定的基質濃度を両立。high cell density perfusion の標準的アプローチ。 |
| `data_requirement_pinn` Data requirement for PINN/hybrid models | Industry rule-of-thumb: hybrid ODE+NN needs ~50-100 batches, pure NN needs 200-500 batches, PINN ~30-80 batches. CHO/... |
| `deep_ensemble` Deep Ensemble UQ | Multiple independently trained networks whose prediction distribution defines mean and variance. Simplest practical U... |
| `digital_twin` Digital Twin (DT) | Virtual replica of the bioreactor process that predicts concentration/state profiles and supports what-if analysis. I... |
| `digital_twin_calibration` Digital Twin calibration | Online/offline parameter estimation and model-mismatch correction using real batch data. Required to keep the DT alig... |
| `efi_pinn` EFI-based UQ for PINN | Extended Fiducial Inference for PINNs. Avoids subjective priors/dropout rates by solving data-generating equations; s... |
| `extracellular_reaction_model` Extracellular Reaction Model | Model of abiotic reactions in culture media, e.g. glutamine degradation. |
| `gp_bias_correction` GP bias correction for plant_model | Gaussian Process that learns the residual between Manstein ODE predictions and observed run data. Natural Phase 2 ext... |
| `hmi_dashboard` HMI ダッシュボード | 研究者が培養状態・承認待ち・アラート・BO 提案を一目で把握するメイン画面。CPP 現在値・トレンド・phase・承認キューを表示し、on-the-loop の接点となる。 |
| `human_on_the_loop` Human-on-the-loop | 監視・判断・包絡線内アクションは自律、包絡線外や重大アクションは人の承認を要する運転形態。auto_cell A 層の自律度。 |
| `approval_workflow` Human-on-the-loop 承認ワークフロー | requested → pending → approved/rejected/timeout → executed/cancelled の状態遷移。タイムアウト時は安全側に倒す。  [merged from multiple age... |
| `hybrid_ode_nn` Hybrid ODE + Neural Network model | Mechanistic ODE structure (mass balances) with kinetic terms represented or corrected by neural networks. More data-e... |
| `icd_setpoint_envelope` ICD setpoint envelope | 協業 ICD に定義された設定点範囲・単位・変化率制限。validate_tool_call と gateway 側の二重検証に使われる。 |
| `l0_fail_safe` L0 フェイルセーフ | ブレイン/通信断時に局所 PID が最終検証済 setpoint を保持し続ける設計。ブレイン停止時も培養を継続させる。 |
| `l0_local_pid` L0 局所 PID | バイオリアクター本体の局所コントローラ。温度/pH/DO/撹拌の高速安全ループを秒オーダで決定的に制御する。 |
| `mpc_roadmap_l1` L1 MPC 導入ロードマップ | Phase 1: ルールベース L1。Phase 2: plant_model ベース MPC シミュレーション・単一操作変数（perfusion rate）。Phase 3: 多変数・適応・経済 MPC の実機適用。 |
| `recipe_executor` L1 決定的レシピ実行器 | ADR-0001 で採用された L1 層。レシピ DSL とルールエンジンに基づき、灌流/給餌/撹拌/サンプリング/継代要否を状態とレシピから決定的に実行する。LLM は per-cycle には入らない。 |
| `state_machine_l1` L1 状態機械 | L1 レシピ実行器内のフェーズ遷移（seed → perfusion_ramp → passage_ready → hold 等）を明確に管理する状態機械。 |
| `llm_orchestrator` L3 薄い LLM オーケストレータ | ADR-0001 で採用された L3 層。ワークフロー dispatch、曖昧知覚解釈、新規例外処理、研究者対話・承認仲介をイベント駆動で実行。定常制御には関与しない。 |
| `mc_dropout` MC Dropout UQ | Dropout retained at inference time to approximate Bayesian predictive distributions. Sensitive to dropout-rate choice... |
| `mpc_vs_rule_engine` MPC vs ルールエンジン比較 | v1 の L1 決定的ルールと将来 MPC との比較軸：実装コスト、検証性、最適性、柔軟性、Annex 22 対応、Human-on-the-loop。v1 はルール、Phase 2 以降は MPC 拡張。 |
| `mpc_fail_safe` MPC フェイルセーフ | MPC ソルバー非収束・異常予測・制約違反時に、L1 が最後の検証済 setpoint または安全側デフォルト灌流率を保持する機構。 |
| `mpc_model_types` MPC モデルタイプ | 線形 MPC（LMPC）、非線形 MPC（NMPC）、経済 MPC（EMPC）、ハイブリッド MPC（PINN+ODE）、データ駆動 MPC（DARX/サブスペース）の分類。A 層では plant_model（Manstein ODE... |
| `mpc_prediction_horizon` MPC 予測ホライズン | MPC が未来のプロセス挙動を予測する時間幅。iPSC 培養ではバッチ尺が数日～数週間のため、時間単位～日単位の予測ホライズンが妥当。CHO fed-batch 例では 30 日が報告されているが、iPSC では未確定。 |
| `mpc_control_horizon` MPC 制御ホライズン | MPC が最適化する未来の操作変数系列の長さ。予測ホライズン以下。iPSC では求解コストと制御性能のトレードオフで選定。CHO 例では 8 日。 |
| `mpc_constraints` MPC 制約集合 | MPC で考慮する制約群：CPP 包絡線（glucose/lactate/osmolality/aggregate diameter）、perfusion rate 範囲（0–7 vvd）、pump ramp 制限、凝集体シア上限、培... |
| `mpc_adaptive_update` MPC 適応更新 | オンライン/at-line データを用いて MPC 内部モデルのパラメータを逐次更新する機構。プロセス・モデルミスマッチ、細胞株変動、ドナー変動に対応。 |
| `mpc` Model Predictive Control | プロセスモデルを用いて未来の挙動を予測し、制約内で最適な操作変数を逐次計算する制御手法。A 層では灌流率・feed bolus を操作変数とする将来拡張候補。 |
| `model_mismatch_correction` Model mismatch correction | Learned correction that refines low-fidelity digital twin or simulation predictions using real data. Essential for tr... |
| `multifidelity_pinn` Multi-fidelity PINN/DT integration | Use of Manstein ODE and Hybrid ODE+NN as low/medium-fidelity surrogates and real bioreactor runs as high-fidelity eva... |
| `neural_ode` Neural ODE | Learned ordinary differential equation dx/dt = f_theta(x). Can be combined with known physics (UDE) for bioreactor dy... |
| `pinn_mpc` PINN-based Model Predictive Control | MPC that uses a PINN as the prediction model instead of a numerical ODE. Demonstrated in microbial/CHO contexts; iPSC... |
| … | 他 40 件は JSON/TTL を参照 |

</details>

**システム**: Ax Bayesian optimization (`ax_bayesian`)、BoTorch (`botorch`)

### ソフトウェア基盤・相互運用 (`d5`)

デバイス統合標準・ワークフローオーケストレーション・データ基盤。OPC-UA/LADS、SiLA2、MQTT、イベントストア、LIMS 等が含まれる。

**32 ノード** — 概念 22 / システム 0 / プレイヤー 0 / 情報源 10

<details>
<summary>主要概念 (22件)</summary>

| ラベル | 内容 |
|---|---|
| `gateway_cmd_ack` Gateway command/ack correlation | MQTT 5.0 Response Topic + Correlation Data を使った非同期 request-response。冪等キーと Message Expiry Interval による重複/stale コマンド防止。 |
| `lads_actuator_function` LADS Actuator Function | LADS Functional Unit に属する駆動機能。灌流ポンプ、給餌ポンプ、培地交換弁、サンプリング弁等の離散/連続駆動素子を表す。 |
| `lads_controller_function` LADS Controller Function | LADS Functional Unit に属する制御機能。局所 PID（pH/DO/Temp/Agitation）の制御ロジックを内包し、ブレインからの検証済設定点を受け取る。 |
| `lads_functional_unit` LADS Functional Unit | LADS v1.0.0 で定義される機能単位。バイオリアクタ槽を 1 つの仮想デバイスとして集約し、内部に Sensor/Controller/Actuator Function と ProgramManager を持つ。 |
| `lads_program_result` LADS Program/Result | LADS ProgramManager が管理するプログラム（seed/passage/perfusion_ramp/clean）とその実行結果。EBR 導出の原材料となる。 |
| `lads_sensor_function` LADS Sensor Function | LADS Functional Unit に属するセンサ機能（analog/discrete/multi-state）。pH/DO/Temp/Agitation/Capacitance/Raman/Pressure/Level/Foa... |
| `lims` LIMS / LES（情報・実行系） | 検体・試薬・手順・結果を記録/指図する上位システム。デバイス層からのデータを集約し、バッチ記録・トレーサビリティに接続する。 |
| `mpc_implementation_libraries` MPC 実装ライブラリ群 | A 層 MPC 実装候補ライブラリ：CasADi（記号計算）、do-mpc（プロトタイプ・OPC-UA 接続例あり）、acados（高速組み込み C コード生成）。 |
| `mqtt_topic_contract` MQTT topic contract | auto_cell brain と device_gateway 間の MQTT topic 命名規則。cell/{culture_unit_id}/{direction}/{category}/{device_id}/{functi... |
| `mtp` MTP（モジュール型パッケージ） | モジュール式・柔軟自動化を可能にする記述。SiLA2と組み合わせ、R&Dから製造へのスケールを支える構成管理の枠組み。 |
| `opcua` OPC-UA / LADS | 産業で普及するM2M標準OPC-UAと、その研究室向けコンパニオン規格LADS。SiLA2と並ぶデバイス通信の選択肢で、製造ライン連携に強い。【P3】LADS v1.0.0(2024年1月, OPC Foundation+Specta... |
| `sila` SiLA 2（デバイス標準） | HTTP/2＋Protocol BuffersとFeature Definition Languageで意味的に同一なデバイスIFを標準化。ベンダロックイン回避と統合工数削減の中核。 |
| `sila_feature` SiLA2 Feature | SiLA2 Feature Definition Language（FDL）で定義される機能単位。サンプリングロボ、分注、at-line 分析器等のコマンド/property を記述。 |
| `tool_set_agitation_rpm` tool: set_agitation_rpm | LADS controller Function / DomainVertical tool for agitation setpoint. |
| `tool_set_perfusion_rate` tool: set_perfusion_rate | LADS controller Function / DomainVertical tool for perfusion rate. Maps to devprofile. |
| `tool_trigger_passage` tool: trigger_passage | LADS Program / DomainVertical tool for dissociation passage with Y-27632. |
| `event_store` イベントストア | 時系列のイミュータブルイベントログを格納するデータ基盤。EBR導出、監査証跡、LADS Program/Result対応の基盤。 |
| `devprofile` デバイスプロファイル / ICD（協業の成果物） | 協業でデバイス側に実装を指定する単一の情報モデル(Interface Control Document)。LADS/OPC-UAのFunctional Unit/Function/Programで表現し、これがdevice実装とaut... |
| `datamodel` データモデル / インジェスト | 画像・センサ・操作ログの標準化された取り込み。新旧機器の異種IFを跨いだ「データ取り込みギャップ」の解消が自律運転の前提。 |
| `gateway` レガシーデバイス・ゲートウェイ | 独自IFしか持たない既存機器を標準IFへ橋渡しするゲートウェイ層。GPIO/USB/シリアル接続と遠隔監視で「スマート化」する。 |
| `orch` ワークフロー・オーケストレーション | タスクとデータと物理ハードを途切れなく統合する制御フレーム（AlabOS, Helao 等）。各機器をサービス化し横断ワークフローを管理。 |
| `idempotency` 冪等性 | L1→L0 の setpoint 変更を idempotency key 付き request-response とし、ブレイン再起動後も同一コマンドを再発行可能にする性質。 |

</details>

### GMP・規制・データインテグリティ (`d6`)

製造ソフトが満たすべき規制・品質・電子記録の要件群。ALCOA+、Part 11、CSV/CSA、EBR、監査証跡、Annex 22 対応などの設計制約を規定する。

**52 ノード** — 概念 40 / システム 0 / プレイヤー 0 / 情報源 12

<details>
<summary>主要概念 (40件)</summary>

| ラベル | 内容 |
|---|---|
| `part11` 21 CFR Part 11 / Annex 11 | 電子記録・電子署名の監査性と安全な取扱いを求めるFDA/EU規制。電子系の設計（権限・署名・改ざん防止）の直接要件。 |
| `alcoa` ALCOA+ データインテグリティ | 帰属性・判読性・同時性・原本性・正確性＋αを全ライフサイクルで満たす原則。製造/解析で生成する全データが従うべき設計要件。 |
| `capa` CAPA / リスク管理（FMEA） | 逸脱・品質事象の根本原因分析と是正/予防措置。FMEA等のリスク評価が製品・工程設計の判断を導く。ソフトの逸脱検知設計に直結。 |
| `csv` CSV / CSA（システムバリデーション） | 計算機システムが目的適合かつALCOA+準拠であることを文書化した証拠。技術的統制で担保するのは複雑で時間を要するが必須工程。 |
| `ebr_derivation` EBR導出ビュー | 1培養ラン=1EBRをevent_storeから導出するためのビュー。R&D一次ではEBR-like実験プロビナンスレポートとして運用。 |
| `gamp_ai_lifecycle` GAMP5 AI ライフサイクル | ISPE GAMP 5 Appendix D11 及び GAMP AI Guide が定める concept / project / operation / retirement の AI 有効化システムライフサイクル。Annex 2... |
| `gctp` GCTP（再生医療等製品製造管理） | 再生医療等製品の製造・品質管理基準。製造設備に加え管理手法の適合性をPMDAが調査。製造ソフトの設計境界を規定する。 |
| `hitl` Human-in-the-Loop（HITL） | AI 出力を適格な人間がレビュー・承認する仕組み。Annex 22 では非クリティカル AI やテスト負荷が軽減されたクリティカル AI で要求される。auto_cell では Human-on-the-loop として実装。 |
| `human_approval` Human-on-the-loop 承認 | 包絡線を外れる setpoint 変更、継代実行、BO 提案採用、緊急停止/ホールド等に対する研究者/オペレータの承認。 |
| `llm_validation` LLM層検証戦略 | L3薄いLLMオーケストレータの非決定性を抑え、プロンプトバージョニング・出力根拠ログ・性能モニタリングでGAMP5 AI/ML要件に対応する戦略。 |
| `mpc_human_on_the_loop` MPC Human-on-the-loop | MPC の提案軌道・包絡線外 setpoint・低信頼度予測に対して研究者が承認/調整/却下する仕組み。Annex 22 対応の決定論的下位制御器としての位置づけと両立。 |
| `annex22` PIC/S GMP Annex 22（AI） | PIC/S・EU GMP の AI/ML 専用アネックス（2025-07-07 草案公開）。クリティカル用途では静的・決定論的 AI/ML モデルのみ許容し、動的学習・確率的出力・生成 AI/LLM を禁止。非クリティカル用途の生成 ... |
| `prediction_confidence_score` Prediction confidence score | Normalized score derived from model predictive uncertainty (e.g. 95% CI width). Drives Human-on-the-loop escalation f... |
| `raman_model_lifecycle` Raman モデルライフサイクル管理 | Raman PLS モデルの version 管理、再校正トリガ（培地ロット変更、細胞株変更、プローブ交換、スケール変更）、性能モニタリング、監査証跡を含む技術的統制。ALCOA-lite・GAMP5 AI/ML Appendix D... |
| `critical_ai` クリティカル AI | 患者安全・製品品質・データインテグリティに直接影響する GMP 判断を支援・自動化する AI/ML モデル。Annex 22 では静的・決定論的モデルのみ許可され、厳格な検証・監視・説明性が求められる。 |
| `validate_tool_call` ツール呼び出し検証 | 副作用ツール呼び出し前に CPP 包絡線・変化率制限・競合を決定的に検証する仕組み。 |
| `test_data_independence` テストデータ独立性 | テスト用データが訓練・検証に使用されないよう技術的・手続き的に保証すること。Annex 22 6.Test Data Independency で要求。 |
| `data_lifecycle` データライフサイクル管理 | 生データの生成・処理・レビュー・保存・検索・廃棄までのALCOA+/Endurable/Availableを担保するライフサイクル管理。 |
| `data_segregation` データ分離 | 訓練・検証・テスト・運用データを分離し、混同・漏洩を防ぐ技術的管理。Annex 22 の test data independency と運用監視の前提。 |
| `drift_monitoring` ドリフト監視 | AI モデルの性能劣化や入力データ分布の変化を継続的に監視する仕組み。Annex 22 10.Operation で要求。 |
| `confidence_score` 信頼度スコア | AI モデルの予測・分類ごとの信頼度を数値化したもの。Annex 22 では低信頼度出力を undecided として人間レビューへルーティングすることを求める。 |
| `ramlaw` 再生医療等安全性確保法 / 施設基準 | 細胞培養加工施設の構造設備基準と適合性調査の根拠法。my iPS製造施設はこの枠組みでPMDA適合性調査を受け稼働を目指す。 |
| `dynamic_model` 動的 AI モデル | 使用中又は新データを継続的・自動的に学習し性能を適応させるモデル。Annex 22 ではクリティカル GMP 用途で禁止。 |
| `approval_log` 承認記録 | Human-on-the-loopにおけるrequested→approved/rejected/timeout→executed/cancelledの承認状態遷移を記録する監査証跡。 |
| `tech_control` 技術的統制 | R&D一次でありつつ将来GMP移行を妨げないよう、ソフトウェアに織り込むALCOA+/Part11/CSV/CSA/EBR/CAPAの実装上の統制群。 |
| `deterministic_output` 決定論的出力 | 同一入力に対し同一出力を返すモデル特性。Annex 22 クリティカル用途で必須。 |
| `feature_attribution` 特徴量帰属 | モデル出力に寄与した入力特徴量を特定・記録する技術。XAI の中核。Annex 22 8.Explainability で要求。 |
| `generative_ai` 生成 AI | テキスト・画像等を生成する確率的モデル群。クリティカル GMP 用途では禁止され、非クリティカル用途で HITL 下でのみ使用可能。 |
| `add_aggimg_human_approval_imaging` 画像品質代理指標の Human-on-the-loop | DL 品質代理指標を BO 目的関数や passage トリガに使う場合、予測不確実性・OOD 検出により低信頼度の場合は研究者承認を必須とする。GAMP5 AI/ML Appendix D11 に準拠したモデル管理が前提。 |
| `audit_ui` 監査/EBR UI | event_store から 1 培養ランの操作ログ・イベント・承認履歴を検索/エクスポートするビュー。ALCOA+ と EBR 再構成を支援。 |
| `audit_schema` 監査ログスキーマ | 副作用ツール呼び出し、承認状態遷移、センサ取り込み、システム状態変化をALCOA+/Part11準拠で記録するための構造化ログスキーマ。 |
| `audit` 監査証跡（Audit Trail） | 誰が・いつ・何を変更したかを追える記録。データインテグリティとPart11準拠の中核で、全操作のロギング設計が必要。 |
| `probabilistic_model` 確率的 AI モデル | 同一入力でも異なる出力を生じうるモデル。Annex 22 ではクリティカル GMP 用途で禁止。 |
| `staff_independence` 職員独立性 | テストデータにアクセスした職員が同じモデルの訓練・検証に関与しないこと。不可能な場合は dual control/4-eyes で緩和。Annex 22 6.5 で要求。 |
| `xai` 説明可能 AI（XAI） | AI 判断の根拠を人間が理解・監査できる技術。Annex 22 では特徴量帰属（feature attribution）の記録を要求。SHAP・LIME・ヒートマップ等が例。 |
| `ebr` 電子バッチ記録（EBR） | 製造工程で生成される改ざん不能な電子記録。前工程データの検証で次工程の整合を担保し、逸脱時の是正を可能にする。 |
| `esignature` 電子署名 | 電子的な承認・検証を行う仕組み。R&D 一次では PIN/パスフレーズ+監査ログで済ませ、GMP 移行時に 21 CFR Part 11 / Annex 11 準拠の完全電子署名へ移行。 |
| `static_model` 静的 AI モデル | デプロイ後に新データを取り込んで性能を適応させない凍結モデル。Annex 22 クリティカル用途で要求される。 |
| `static_deterministic_proof` 静的決定論的証明 | AI モデルが静的（凍結パラメータ）かつ決定論的（同一入力→同一出力）であることを、チェックサム・固定シード・再現性テスト・モデルカードで証明する手法。 |
| `noncritical_ai` 非クリティカル AI | 文書作成、トレーニング、スケジューリング、非 GMP 傾向分析など、患者安全・品質・データ完全性に直接影響しない AI。生成 AI/LLM も HITL 下で使用可能。 |

</details>

### センサ・環境モニタリング (`d7`)

培養環境・代謝物・細胞密度・凝集体径・無菌性の連続/アットライン計測と、閉ループ制御への状態量供給。CPP 定義と計測機器が集約される。

**72 ノード** — 概念 35 / システム 9 / プレイヤー 0 / 情報源 28

<details>
<summary>主要概念 (35件)</summary>

| ラベル | 内容 |
|---|---|
| `cpp_aggregate_diameter` CPP: aggregate diameter | A-layer aggregate diameter 150-350 um; Borys 2021 reports >400 um necrosis risk. |
| `cpp_ammonia` CPP: ammonia (monitoring) | Ammonia monitoring-only CPP for v1; mammalian toxicity threshold 4-6 mM, iPSC-native threshold not yet established. |
| `cpp_do` CPP: dissolved oxygen | A-layer DO setpoint 40% -> 10% at high density; L0 local PID with agitation cascade. |
| `cpp_glucose` CPP: glucose | A-layer glucose >1.5 mM; K_Glc=1.5 mM from Manstein 2021 Table 1; perfusion trigger source. |
| `cpp_glutamine` CPP: glutamine | A-layer glutamine >0.01 mM; K_Gln=0.01 mM from Manstein 2021 Table 1. |
| `cpp_lactate` CPP: lactate | A-layer lactate <50 mM; K_Lac=50 mM from Manstein 2021 Table 1; perfusion trigger source. |
| `cpp_osmolality` CPP: osmolality | A-layer osmolality <500 mOsm/kg; K_Osm=500 mOsm/kg from Manstein 2021 Table 1; perfusion trigger source. |
| `cpp_ph` CPP: pH | A-layer pH setpoint 7.1; L0 local PID maintains, L1 may shift within envelope. |
| `cpp_temp` CPP: temperature | A-layer temperature setpoint 37 C; L0 local PID. |
| `cpp_viability` CPP: viability | A-layer viability target >90%; primarily BO objective input, not L1 control target. |
| `cpp_vcd` CPP: viable cell density | A-layer VCD target ~35e6 cells/mL; measured by in-line capacitance; triggers passage. |
| `measurement_fbrm_cld` FBRM 弦長分布計測 | Mettler Toledo ParticleTrack による Focused Beam Reflectance Measurement。連続計測可能だが、CLD は真の粒径分布ではなく凝集体形状に依存。 |
| `add_aggimg_fbrm_cld_detail` FBRM 弦長分布（CLD）解析 | Focused Beam Reflectance Measurement による in-line chord length distribution。0.5–1000 µm のトレンド監視が可能。CLD は真の粒径分布ではなく、凝集体... |
| `raman_reference_nova` Nova FLEX2 Raman 正解ラベル | Raman PLS モデルの校正に使用する at-line リファレンス計測。Nova BioProfile FLEX2 による glucose/lactate/glutamine/osmolality/viability/細胞径等の... |
| `measurement_ovizio_dhm` Ovizio D3HM ホログラフィ計測 | Ovizio iLINE-F PRO の Double Differential Digital Holographic Microscopy。ラベルフリー連続細胞/凝集体モニタリング。iPSC 実証は限定的。 |
| `raman_aggregate_interference` Raman 凝集体干渉 | 凝集体径・密度の増大が Raman プローブの光路長と散乱断面積を変化させ、代謝物推定精度を低下させる要因。凝集体径は培養日数とともに増大し（95 µm → 530 µm）、多能性維持のため 400 µm 以下が推奨される。〔事実：E... |
| `raman_cell_scattering` Raman 細胞光散乱 | 懸濁細胞・凝集体による Mie 散乱により Raman 強度が減衰する現象。Beer-Lambert 則では記述できず、細胞密度との非線形関係が知られる。iPSC 凝集体（150–350 µm）は 785 nm レーザーに対して大きな... |
| `measurement_atline_nova` at-line Nova FLEX2 マルチパラメータ | Nova BioProfile FLEX2 による 16 項目（代謝物/ガス/電解質/細胞密度/生存率/細胞径/浸透圧）のアットライン分析。Raman 校正・BO 入力の正解ラベル源。 |
| `monitoring_ammonia_atline` at-line アンモニウムモニタリング | Nova FLEX2 による NH4+ のアットライン計測。CPP ではないが、代謝毒性早期発見のため監視。 |
| `measurement_aggregate_imaging` at-line 凝集体画像計測 | FlowCam または Kropp 型バイパス顕微鏡による凝集体径・形態の画像解析。v1 では離散/日次運用が現実的。 |
| `raman_calibration_ipsc` iPSC 浮遊凝集体 Raman 校正戦略 | iPSC 浮遊/凝集体バイオリアクターにおける in-line Raman の再校正アプローチ。Nova FLEX2 を正解ラベル、capacitance を VCD anchor、凝集体画像を光散乱補正の共変量として用いる。CHO ... |
| `measurement_raman_inline` in-line Raman 代謝物計測 | in-line Raman 分光による glucose/lactate/glutamine/glutamate の同時推定。CHO で PID 閉ループ実証あり。iPSC では chemometric 再校正が必要。 |
| `measurement_vcd_capacitance` in-line capacitance VCD | Aber/Hamilton/Sartorius 等の誘電分光/インピーダンスセンサによる生細胞密度の連続計測。iPSC 高密度では offline VCD・細胞径・生存率を用いた校正が必要。 |
| `monitoring_quality_offline` offline 品質マーカー計測 | 未分化/多能性マーカー（OCT4/SOX2/NANOG/SSEA/TRA）、核型/同一性、自発分化等の offline/run 単位計測。BO 目的関数専用。 |
| `monitoring_sterility_offline` offline/rapid 無菌性計測 | 汚染/無菌性の offline または rapid micro 検査。現時点で検証済み online 手段は未確認。CAPA トリガ源。 |
| `add_cho_ipsc_ammonia_threshold` アンモニア閾値の未確定性 | CHO では 5 mM で成長阻害が報告されるが、iPSC のネイティブ閾値は未確定。auto_cell A 層では監視値として扱い、実データまたは文献調査で再校正。 |
| `cpv` インライン/アットライン分析（CPV） | 工程内・近接でのリアルタイム計測で工程性能を継続検証(CPV)。AI/自動化が高スループットQCと工程安定性監視を可能にする。【P5】具体スタック(2026-06-15調査): VCD=in-line capacitance(Aber... |
| `edge` エッジセンサ統合 | マイコン/IoTによる多点センサ取得とデバイス層への配信。標準IF（SiLA2/OPC-UA）やゲートウェイ経由で上位へ集約する接点。 |
| `add_cho_ipsc_glucose_threshold` グルコース閾値の細胞種差 | CHO では 2–3 g/L（11–17 mM）維持が推奨される。iPSC では Manstein 2021 が K_Glc=1.5 mM を採用。iPSC は低グルコースで飢餓制限を受けやすい。 |
| `add_cho_ipsc_lactate_threshold` 乳酸閾値の細胞種差 | CHO では株により 15–50 mM の阻害閾値が報告される。iPSC では Manstein 2021 のモデル値 K_Lac=50 mM が用いられるが、実際の iPSC 株・培地で再校正が必要。CHO 値をそのまま転用しない。 |
| `add_aggimg_brightfield_atline` 明視野/位相差 at-line 凝集体画像 | iPSC 浮遊凝集体で最も普及している at-line 画像計測。サンプリング＋光学顕微鏡＋ImageJ 等で径・形態を手動/半自動計測。Kropp 型バイパス顕微鏡または自動サンプリング＋顕微鏡で自動化可能。 |
| `contamination_response` 汚染疑い応答フロー | contamination_suspected 検知時の P0 即時対応。ブレインは安全系へのホールド要求を出し、デバイス局所が強制停止。研究者確認・誤検知記録・CAPA 起票の分岐。 |
| `add_cho_ipsc_osmolality_threshold` 浸透圧閾値の細胞種差 | CHO/哺乳類培養では 380–450 mOsm/kg 超で成長低下が報告される。iPSC では Manstein 2021 が K_Osm=500 mOsm/kg を採用。培地・密度依存で再校正要。 |
| `sterility` 無菌性・コンタミ監視 | 菌混入や逸脱の検知。閉鎖系では更衣簡略化と引換えに監視設計が重要で、9日連続運転でも重大エラー/汚染ゼロが品質目標水準。 |
| `envmon` 環境モニタリング（DO/pH/CO₂/温度） | 培養環境の連続計測。維持培養や量産の安定性を支え、閉ループ制御の状態量を供給する。エッジ実装（ESP32等）で分散計測が可能。 |

</details>

**システム**: Aber FUTURA (`instr_aber_futura`)、DHM / Ovizio iLINE-F PRO (`add_aggimg_dhm_ovizio`)、FlowCam (`instr_flowcam`)、FlowCam at-line 凝集体画像 (`add_aggimg_flowcam_atline`)、Hamilton Incyte Arc (`instr_hamilton_incytes`)、Mettler Toledo ParticleTrack G400 (`instr_fbrm_g400`)、Nova BioProfile FLEX2 (`instr_nova_flex2`)、Ovizio iLINE-F PRO (`instr_ovizio_ilinef`)、Sartorius BioPAT ViaMass (`instr_sartorius_viamass`)

### エコシステム・プレイヤー (`d8`)

財団・企業・装置など実在の担い手と製品。技術選定とパートナリングの地図。

**15 ノード** — 概念 0 / システム 6 / プレイヤー 5 / 情報源 4

**システム**: Molecular Devices / CellXpress.ai (`moldev`)、Robotic Biology Institute / Maholo (`rbi`)、SiLA2 at-line 分析器 (`peripheral_atline_analyzer`)、SiLA2 サンプリングロボ (`peripheral_sampler`)、SiLA2 自動分注器 (`peripheral_dispenser`)、Terumo BCT / Quantum Flex (`terumo`)

**プレイヤー**: CiRA財団 / my iPS (`cira`)、Epistra（自律最適化） (`epistra`)、アステラス製薬（双腕ロボ） (`astellas`)、カネカ × 理研（林洋平ら） (`kaneka`)、パナソニックHD (`pana`)

## 情報源トップレベル一覧

主要な一次情報源（文献・規格・製品ページ）をまとめます。

| ID | ラベル | 内容 |
|---|---|---|
| `src_mqtt5_reqresp` |  |  |
| `src_sila_comm` |  |  |
| `src_part11` | 21 CFR Part 11 | FDA regulation 'Electronic Records; Electronic Signatures'。電子記録・電子署名・監査証跡の技術的要件を定める。 |
| `src_aber_futura` | Aber FUTURA app note | Aber Instruments, FUTURA capacitance perfusion monitoring. |
| `src_abu_absi_2011` | Abu-Absi et al. 2011 in-line Raman CHO | Real time monitoring of multiple parameters in mammalian cell culture bioreactors using an in-lin... |
| `src_add_cho_ipsc_amsbio` | Amsbio stem cell QC guide | 幹細胞品質管理ガイド。OCT4/SOX2/NANOG/SSEA/TRA 等の多能性マーカー。 |
| `src_ax` | Ax Adaptive Experimentation Platform | Facebook/Meta の実験最適化プラットフォーム。BoTorch 上に構築され、探索空間・制約・多忠実度の管理に向く。 |
| `src_berry_2015` | Berry et al. 2015 cross-scale Raman CHO | Cross-scale predictive modeling of CHO cell culture growth and metabolites using Raman spectrosco... |
| `src_bioprocessintl_2026` | Bioprocess International 2026: Multifidelity Optimization in Biopharma | Case study of multi-fidelity BO in mAb process with mechanistic simulator bias up to 15%. |
| `src_bioprocesstools_raman` | Bioprocess Tools Raman monitoring guide | How to Use Raman Spectroscopy for Real-Time Bioprocess Monitoring. PLS モデル構築ワークフロー、前処理、5–15 バッチ校正... |
| `src_bioprocesstools_2026` | Bioprocesstools 2026: AI and ML for Bioprocess Optimization | Industry survey of ML method data requirements for bioprocess optimization. |
| `src_botorch` | BoTorch（ベイズ最適化） | PyTorch ベースのベイズ最適化ライブラリ。多忠実度・制約付き BO に強く、L2 層の実装候補。 |
| `src_borys` | Borys et al. 2021 (Stem Cell Res Ther) | iPSC Vertical-Wheel(PBS Biotech)撹拌最適化。40rpmが最大増殖(day6で32.3±3.2倍)、day5凝集体径169-275µm、>400µmで壊死予想。撹拌... |
| `add_aggimg_src_borys_2021` | Borys et al. 2021 (hiPSC Vertical-Wheel) | Vertical-Wheel 撹拌槽での hiPSC 凝集体培養。40–80 rpm で day 5 径 169–275 µm、>400 µm で壊死リスク。PMC7805206。 |
| `src_add_cho_ipsc_borys2021` | Borys et al. 2021 Vertical-Wheel hiPSC | Vertical-Wheel 撹拌槽での hiPSC 凝集体拡大。40 rpm 最適、>400 µm で壊死リスク。 |
| `src_cgt` | CGT QC/QA（ALCOA・Part11） | データインテグリティ・CSV・CAPA・CPVを横断する実務解説。電子系設計の要件マップとして有用。 |
| `src_cobrapy` | COBRApy | Python によるゲノム規模代謝モデリングライブラリ。将来の COBRApy+GEM バックエンド差替の基盤。 |
| `src_casadi` | CasADi | 非線形最適化と自動微分のためのオープンソース記号計算フレームワーク。MPC モデリングの基盤。 |
| `src_catalao_2025` | Catalão et al. 2025 (J Process Control) | Bioprocess MPC with physics-informed neural networks, microbial community PHA production. |
| `src_cxa` | CellXpress.ai 適用ノート | コンフルエンシー/分化のDL2モデルと閾値起動の自動継代を具体記述。画像→意思決定の設計参照。 |
| `src_add_cho_ipsc_chen2014` | Chen et al. 2014 hPSC culture considerations | hPSC 培養の維持・拡大・治療応用における考慮事項。酸素拡散限界 100–200 µm。 |
| `add_aggimg_src_chu_2023` | Chu et al. 2023 (iPSC reprogramming DL) | 明視野時系列画像から hiPSC 形成・コロニー形態を予測。CNN+U-Net+RNN。accuracy 0.8。DOI 10.1016/j.cmpb.2022.107264。 |
| `src_costa_2024` | Costa et al. 2024 Raman cell therapy review | Harnessing Raman spectroscopy for cell therapy bioprocessing. Biotechnol Adv 2024. Cell therapy 製... |
| `src_eu_ai_act` | EU AI Act (Regulation 2024/1689) | 欧州 AI 規則。製造プロセス制御等の high-risk AI に透明性・文書化・人間監視を要求。Annex 22 と併用される。 |
| `add_aggimg_src_eppendorf_485` | Eppendorf App Note 485 (hiPSC stirred-tank) | 1 L DASGIP Spinner Vessel での hiPSC 凝集体拡大。day 0–5 で 0.5×10⁶ → 8×10⁶ cells/mL。凝集体径は at-line 明視野画像＋I... |
| `src_annex11` | EudraLex Annex 11 | EudraLex Volume 4 Annex 11 — Computerised Systems。EUのGMPデータコンピュータ化システム要件。 |
| `src_fda_data_integrity` | FDA 2018 Data Integrity Guidance | FDA 'Data Integrity and Compliance With Drug CGMP Questions and Answers' (2018)。ALCOA+原則を医薬品製造のデー... |
| `src_fda_csa` | FDA CSA Guidance | FDA 'Computer Software Assurance for Production and Quality System Software' (2022 draft / 2025 f... |
| `src_flowcam` | FlowCam overview | Fluid Imaging Technologies, FlowCam imaging particle analyzer overview. |
| `add_aggimg_src_flowcam` | FlowCam 技術資料 | フローイメージング顕微鏡。2 µm–1 mm の粒子/凝集体画像解析。高濃度・重なり時は計数漏れ。 |
| `src_add_cho_ipsc_gfi2025` | GFI 2025 Cultivated meat techno-economics report | 哺乳類細胞培養における乳酸・浸透圧の阻害メカニズムと閾値範囲。CHO 培養知見を含む。 |
| `src_galv` | Galvanauskas et al. 2019 (近縁の3項モデル) | iPSC浮遊培養速度論の近縁モデル(Galvanauskas/Kino-Oka 2019, Regen Therapy 12:88-93)。グルコースMonod＋乳酸阻害＋凝集体体積阻害の3項の... |
| `src_raman_graf2022` | Graf/Wei 2022 in-line Raman PID glucose | Graf/Wei et al. 2022, Frontiers in Bioengineering, in-line Raman closed-loop glucose control. |
| `add_aggimg_src_gursky_2023` | Gursky 2023 (hPSC morphology review) | hPSC 形態と自動評価のレビュー。培地・マトリックス・細胞株による形態変動を指摘。 |
| `src_hamilton_incytes` | Hamilton Incyte Arc specs | Hamilton Company, Incyte Arc Viable Cell Density Sensor specifications. |
| `src_huang2020` | Huang et al. 2020 (Cell Gene Therapy Insights) | PSC 10 L スケールアップ。動的灌流で pH 6.8 トリガー + 30%/日増加、固定灌流比 25% 向上、乳酸 15 mM 未満抑制。 |
| `src_add_cho_ipsc_huang2020` | Huang et al. 2020 PSC 10L stirred tank manufacturing | 10 L 撹拌槽での PSC 製造プロセス開発。凝集体サイズ 300 µm 制限、酸素拡散限界 100–200 µm。 |
| `src_iec62366` | IEC 62366-1（医療機器ユーザビリティ） | 医療機器のユーザビリティエンジニアリングを規定する国際標準。HMI 設計の人因工学基準。 |
| `src_isa101` | ISA-101（プロセス制御 HMI 設計） | ISA-101 標準群。プロセス産業向け HMI の視覚設計、アラーム管理、パフォーマンス指向ディスプレイを規定。 |
| `src_gamp5` | ISPE GAMP 5 2nd Edition | ISPE GAMP 5 Guide: A Risk-Based Approach to Compliant GxP Computerized Systems, Second Edition (2... |
| `src_gamp5_ai` | ISPE GAMP Guide: Artificial Intelligence | ISPE GAMP Guide: Artificial Intelligence (2025)。AI有効化コンピュータ化システムのライフサイクル全体の検証・データガバナンス・モデルリスク管理を扱う。 |
| `src_kanda` | Kanda et al. 2022 (eLife) | 自律ロボット×バッチベイズ最適化でiPSC-RPE分化を最適化した記念碑的論文。プロトコルの5段階定式化とパラメータ探索、コード公開を含む。 |
| `add_aggimg_src_kato_2016` | Kato et al. 2016 (colony morphology & gene expression) | hPSC コロニー形態のパラメトリック解析。形態カテゴリと遺伝子発現プロファイルが対応。Sci Rep 6:34009。 |
| `src_krause2023` | Krause 2023 capacitance review | Krause et al. 2023, Curr Opin Biotechnol, biocapacitance online biomass monitoring. |
| `src_kropp` | Kropp/Lipsitz et al. 2015 (BMC Proceedings) | hPSC撹拌懸濁のBox-Behnken DoE。pH7.3/37℃、毎日給餌で高密度、播種2×10⁵が最適、DOは本研究で非有意。注: HES2(ESC)・Micro-24振盪式(400rpm... |
| `add_aggimg_src_kropp_2019` | Kropp/Lipsitz et al. 2019 (hiPSC bypass imaging) | hiPSC 撹拌懸濁培養の at-line バイパス顕微鏡画像。凝集体径・形態の自動計測への先行例。DOI 10.1038/s41598-019-48814-w。 |
| `src_mqtt5` | MQTT Version 5.0 ｜ OASIS Standard | MQTT 5.0 標準仕様。Response Topic、Correlation Data、Message Expiry Interval、Reason Code 等により request-re... |
| `src_add_cho_ipsc_mabion2025` | Mabion 2025 CHO metabolite analysis guide | CHO 培養の代謝物/栄養解析に関する業界ガイダンス。乳酸・アンモニア・浸透圧の影響。 |
| `src_machleidt_2024` | Machleidt et al. 2024 cross-clone Raman CHO | Feasibility and performance of cross-clone Raman calibration models in CHO cultivation. Biotechno... |
| `add_aggimg_src_maddah_2014` | Maddah et al. 2014 (morphology-based iPSC evaluation) | time-lapse + 形態特徴量による iPSC コロニー品質自動評価。6 特徴量で accuracy 0.80–0.89。 |
| `src_add_cho_ipsc_manstein2021` | Manstein & Zweigerdt 2021 hiPSC perfusion | hPSC 灌流撹拌槽高密度培養。7 日で 35×10⁶ cells/mL、乳酸/浸透圧/グルコース制御、6 項 Monod モデル。 |
| `src_manstein` | Manstein & Zweigerdt 2021（plant_model 原典） | auto_cell Tier2 plant_modelの真の原典。hPSC灌流撹拌槽培養をpH7.1/DO40%/浸透圧ピーク抑制/灌流で制御し、7日で70倍・35×10⁶ cells/mL(1... |
| `src_matthews_2016` | Matthews et al. 2016 Raman 乳酸閉ループ制御 | Closed loop control of lactate concentration in mammalian cell culture by Raman spectroscopy lead... |
| `src_metrohm_an_pan_1065` | Metrohm 2060 Raman cell culture AN-PAN-1065 | Inline monitoring of cell cultures with Raman spectroscopy. Metrohm 2060 Raman Analyzer による細胞培養 g... |
| `add_aggimg_src_fbrm_g400` | Mettler Toledo FBRM 技術資料 | FBRM 原理：回転レーザー後方散乱による chord length distribution。iPSC 凝集体では CLD→径換算に注意。 |
| `src_fbrm_g400` | Mettler Toledo ParticleTrack FBRM | Mettler Toledo, ParticleTrack with FBRM technology. |
| `src_nist_ai_rmf` | NIST AI Risk Management Framework | NIST が公開する AI リスク管理フレームワーク。Human-on-the-loop / human-in-the-loop による AI システムのガバナンスと監視を含む。 |
| `src_nobar_2025` | Nobar et al. 2025 (arXiv) | Guided multi-fidelity Bayesian optimization with learned correction model for digital twin contro... |
| `src_traj` | Nogueira 2019 / Olmer 2012（到達密度 実測） | バッチ vs 灌流の到達密度差。標準バッチはNogueira(Vertical-Wheel)=peak 2.3×10⁶、Olmer(撹拌槽)=2.4×10⁶ cells/mL止まり。plant_... |
| `src_nova_flex2` | Nova BioProfile FLEX2 | 16-parameter at-line analyzer for metabolites, osmolality, viability, cell diameter.  [merged fro... |
| … | 他 38 件 | JSON/TTL を参照 |

## ナレッジグラフの使い方

1. **対話的に探索** → `ips_automation_knowledge_map_v2_1.html` をブラウザで開く
2. **プログラムで取り込み** → `knowledge_graph_v2_1.json` を `json.load()`
3. **SPARQL/Triple store** → `knowledge_graph_v2_1.ttl`
4. **表計算** → `nodes_v2_1.csv` / `edges_v2_1.csv` / `sources_v2_1.csv`

HTML ビューアの操作:
- ドメイン凡例をクリック → 該当ドメインだけソロ表示
- ノードをクリック → 内容・情報源・関係を右パネル表示
- ドラッグ / ホイール → 移動・ズーム
- 検索ボックス → ラベル・内容の全文一致
- EXPORT JSON → 現在の表示状態を JSON 出力
