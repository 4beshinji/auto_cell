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
