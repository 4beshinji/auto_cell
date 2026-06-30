# 閉ループ実現に必要な不足アセット

> 目的: ROADMAP.md・設計再検討レポート・追加調査統合レポートを踏まえ、auto_cell A 層で Sense-Decide-Act ループを閉じるために現時点で欠けているアセットを分類・列挙する。
> Scope: iPSC 浮遊/凝集体バイオリアクター制御（Manstein 型灌流 0→7 vvd）
> 前提: ADR-0001、requirements.md、kg_to_auto_cell.md

---

## 1. アセット分類

| 分類 | 内容 | v1 で必須か |
|---|---|---|
| **A. コア実装** | plant_model、plugin、L1/L2/L3 エンジン、gateway | 必須 |
| **B. 設計仕様** | DSL 文法、MQTT 契約、ICD、承認フロー、信頼度設計 | 必須 |
| **C. 知識・研究ギャップ** | iPSC 固有閾値、Raman 補正、MPC/PINN 構造、DL 代理指標 | 調査必須（実装は後段） |
| **D. 検証・テスト** | golden test、再現性テスト、L1 イベント網羅テスト | 必須 |
| **E. 規制・文書** | Intended Use、モデルカード、静的決定論的証明、ALCOA-lite | 必須（軽量版） |
| **F. インフラ** | event_store、audit_log、virtual_edge、HMI | 必須 |

---

## 2. A. コア実装アセット

### A1. Tier2 plant_model（`sim/plant_model/`）

| # | アセット | 内容 | 優先度 | 備考 |
|---|---|---|---|---|
| A1.1 | Manstein 2021 6 項 Monod ODE | scipy で `solve_ivp` する決定的 ODE | 最高 | `step(actuators) -> sensors` IF が必要 |
| A1.2 | 灌流項 | perfusion_rate_vvd を入力として取り込む | 最高 | 標準バッチでは 35e6 到達不可 |
| A1.3 | アクチュエータベクタ | perfusion_rate, agitation_rpm, do_setpoint, ph_setpoint, feed_glucose, feed_glutamine | 高 | 将来 COBRApy/GEM 差替前提 |
| A1.4 | センサ出力 | vcd, viability, glucose, lactate, glutamine, osmolality, aggregate_diameter_um, do_percent, ph, temp_c | 高 | 決定性契約必須 |
| A1.5 | パラメタテーブル | µmax, K_Glc, K_Lac, K_Gln, K_Osm, K_Agg, q_Glc, q_Lac, q_Gln | 高 | 原典 Manstein 2021 Table 1 |
| A1.6 | ゴールデンテスト | 7 日 35×10⁶ cells/mL 軌道の CI 再現 | 最高 | `tests/test_plant_model.py` |

### A2. cell_culture plugin（`src/auto_cell/plugins/cell_culture/`）

| # | アセット | 内容 | 優先度 | 備考 |
|---|---|---|---|---|
| A2.1 | `environment.py` | `CellCultureEnv` (BaseModel): 全 CPP フィールド | 最高 | `kg_to_auto_cell.md` §3 の environment_model 対応 |
| A2.2 | `channels.py` | `channel_config`, `route_channel` | 最高 | LADS sensor Function 名と対応 |
| A2.3 | `events.py` | `detect_events`, `event_descriptions`, `suppression_defaults` | 最高 | 全イベント判定ロジック |
| A2.4 | `tools.py` | `tool_schemas`, `tool_handlers` | 最高 | set_perfusion_rate, set_agitation_rpm, feed, exchange_media, set_gas_setpoint, trigger_passage, take_sample |
| A2.5 | `sanitizer.py` | `validate_tool_call`, 包絡線・ramp 制限 | 最高 | CHO→iPSC 転用禁止の数値を内包 |
| A2.6 | `prompt.py` | `system_prompt_section`, `build_culture_unit_summary` | 中 | L3 LLM 用 |
| A2.7 | `confidence.py` | 信頼度スコア層 | 中 | Phase 1 基盤、Phase 2 拡張 |
| A2.8 | `drift.py` | ドリフト監視 | 低 | Phase 2 |
| A2.9 | `xai.py` | feature attribution ラッパ | 低 | Phase 2 |

### A3. L1 決定的レシピ/ルールエンジン

| # | アセット | 内容 | 優先度 | 備考 |
|---|---|---|---|---|
| A3.1 | レシピ DSL | YAML/JSON 文法：状態、遷移条件、アクション、タイムアウト | 最高 | `recipe_dsl` |
| A3.2 | 状態機械エンジン | seed → perfusion_ramp → passage_ready → approved_passage → reseed / hold | 最高 | Python state machine |
| A3.3 | ルールエンジン | glucose/lactate/osmolality トリガーから perfusion/feed/exchange を決定 | 最高 | 決定的・再現可能 |
| A3.4 | イベントディスパッチャ | `detect_events` 出力をアクション候補に変換 | 高 | 優先順位制御 |
| A3.5 | アクションプランナー | 副作用ツールの依存関係・競合解消 | 中 | 例: 灌流上昇と培地交換の同時発火 |

### A4. L2 ベイズ最適化エンジン

| # | アセット | 内容 | 優先度 | 備考 |
|---|---|---|---|---|
| A4.1 | BO ラッパ | Ax または BoTorch 直接の薄いラッパ | 高 | `bbo` |
| A4.2 | 探索空間定義 | seeding_density, initial_glucose, perfusion_ramp_profile, max_perfusion_rate, agitation_base_rpm, DO_transition, Y-27632_conc 等 | 高 | Pydantic model |
| A4.3 | 目的関数 | `J = yield × viability × pluripotency% × aggregate_size_score × cost_penalty` | 高 | 重みは研究者合意 |
| A4.4 | 制約定義 | CPP 包絡線、ramp 制限を BO 制約として表現 | 高 | Safe BO |
| A4.5 | 多忠実度接続 | `plant_model.step` を低忠実度評価として呼び出し | 中 | Phase 2 |
| A4.6 | バッチ BO | 多バイオリアクタ並行運転対応 | 中 | Phase 2 |
| A4.7 | 再現性テスト | 固定シードで同じ提案を確認 | 高 | CI |

### A5. L3 薄い LLM オーケストレータ

| # | アセット | 内容 | 優先度 | 備考 |
|---|---|---|---|---|
| A5.1 | トリガー判定 | 承認仲介、曖昧知覚解釈、新規例外、研究者対話 | 中 | イベント駆動 |
| A5.2 | プロンプトテンプレート | システムプロンプト＋現在状態要約 | 中 | バージョニング |
| A5.3 | ツール呼び出しラッパ | `tool_schemas` から LLM 用 schema 生成 | 中 | |
| A5.4 | 入出力ログ | 思考過程・使用ツール・根拠を不変ログ化 | 高 | NFR-X |

### A6. Gateway / Infra

| # | アセット | 内容 | 優先度 | 備考 |
|---|---|---|---|---|
| A6.1 | MQTT broker 接続 | physical-ai-core 経由または standalone | 高 | `infra/virtual_edge/` |
| A6.2 | LADS/OPC-UA クライアント | Functional Unit / Function 購読・method 呼び出し | 中 | Phase 1 後半〜 |
| A6.3 | SiLA2 クライアント | 周辺機器接続 | 中 | Phase 1 後半〜 |
| A6.4 | MQTT topic 実装 | telemetry/event/cmd/ack/program/state/approval/notify/hmi | 高 | `kg_to_auto_cell.md` §7.3 |
| A6.5 | correlation_id 管理 | cmd/ack/approval の紐付け | 高 | 監査用 |
| A6.6 | 仮想バイオリアクター | `infra/virtual_edge/` で MQTT 経由の dummy plant | 高 | 実機前の結線検証 |

### A7. HMI / 承認フロー

| # | アセット | 内容 | 優先度 | 備考 |
|---|---|---|---|---|
| A7.1 | 承認状態管理 | requested → approved/rejected/pending_timeout → executed/cancelled | 高 | |
| A7.2 | 承認キュー UI | 承認待ちアクション一覧 | 高 | |
| A7.3 | ダッシュボード | CPP 現在値・トレンド・phase・承認待ち件数 | 高 | |
| A7.4 | アラート UI | P0–P3 優先度、抑制窓、通知履歴 | 高 | |
| A7.5 | BO 提案レビュー | 次 run パラメータ提案と承認/調整 | 中 | Phase 2 |
| A7.6 | 監査/EBR ビュー | event_store からの実験プロビナンス再構成 | 中 | |

---

## 3. B. 設計仕様アセット

### B1. レシピ DSL 仕様

| # | アセット | 内容 | 優先度 |
|---|---|---|---|
| B1.1 | 正式文法 | YAML/JSON スキーマ：states/transitions/actions/conditions/timeout | 最高 |
| B1.2 | 標準レシピ | Manstein プロトコル（灌流 0→7 vvd、固定設定点、条件起動給餌）を DSL 化 | 高 |
| B1.3 | バリデータ | DSL スキーマ検証、到達不能状態検出 | 中 |

### B2. MQTT / LADS / SiLA2 契約

| # | アセット | 内容 | 優先度 |
|---|---|---|---|
| B2.1 | MQTT topic 命名規則 | `cell/{culture_unit_id}/{direction}/{category}/{device_id}/{function_id}/{aspect}` | 高 |
| B2.2 | 承認 state topic | `cell/{cu}/state/approval/{request_id}` | 高 |
| B2.3 | HMI 通知 topic | `cell/{cu}/notify/hmi/{priority}` | 高 |
| B2.4 | cmd/ack ペイロード | args, correlation_id, timestamp, request_id, status, result | 高 |
| B2.5 | LADS Functional Unit 定義 | `SuspensionBioreactor` の Function 一覧 | 中 |
| B2.6 | SiLA2 Feature 候補 | サンプリングロボ・分注・Nova FLEX2 | 中 |
| B2.7 | ICD ドキュメント | デバイスプロファイル・setpoint 包絡線 | 中 |

### B3. 承認ワークフロー仕様

| # | アセット | 内容 | 優先度 |
|---|---|---|---|
| B3.1 | 承認要否マトリクス | 各 tool/各条件での承認要否 | 高 |
| B3.2 | タイムアウト値 | 包絡線外 setpoint=10 min, trigger_passage=30 min, BO 提案=24 h | 高 |
| B3.3 | タイムアウト時デフォルト | キャンセル/保留/ホールド | 高 |
| B3.4 | 冪等性設計 | 同一 request_id の重複実行防止 | 高 |
| B3.5 | 承認ログスキーマ | who/when/what/why/result | 高 |

### B4. 信頼度スコア層仕様

| # | アセット | 内容 | 優先度 |
|---|---|---|---|
| B4.1 | GP 事後分散 → 信頼度 | L2 BO 提案の不確実性 | 中 |
| B4.2 | PLS Q 残差 / Hotelling T² | Raman 予測信頼度 | 低（Phase 2） |
| B4.3 | DL 予測不確実性 | ensemble / MC dropout / OOD | 低（Phase 2/3） |
| B4.4 | 低信頼度閾値 | 自動 HITL エスカレーション条件 | 中 |
| B4.5 | HMI 表示仕様 | 信頼度スコアと根拠の可視化 | 中 |

---

## 4. C. 知識・研究ギャップ（オンライン調査が必要）

### C1. iPSC 固有プロセスパラメタ

| # | ギャップ | 必要性 | 調査方法 |
|---|---|---|---|
| C1.1 | **アンモニアの iPSC ネイティブ閾値** | L1 イベント化の可否 | 文献サーチ＋実験 |
| C1.2 | **Ramp 制限値の定量的根拠** | シア/浸透圧ショック回避 | 文献サーチ（Borys 2021 等） |
| C1.3 | **CSPR（cell-specific perfusion rate）の実用的範囲** | 培地利用効率・高密度安定性 | 文献サーチ＋実データ |
| C1.4 | **凝集体径分布（>400 µm 割合）と品質の相関** | `large_aggregate_high` イベント信頼性 | 文献サーチ＋実験 |
| C1.5 | **細胞株依存性の大きさ** | CPP 閾値の一般化可能性 | 文献サーチ |

### C2. Raman 校正・光散乱

| # | ギャップ | 必要性 | 調査方法 |
|---|---|---|---|
| C2.1 | **iPSC 浮遊凝集体における Raman 光散乱補正式** | RMSEP 改善 | 論文調査＋実験計画 |
| C2.2 | **capacitance/VCD を共変量とした PLS モデル** | 高密度下の精度 | 論文調査 |
| C2.3 | **必要バッチ数と校正設計** | コスト・精度トレードオフ | 産業事例調査 |
| C2.4 | **CHO→iPSC モデル転移可能性** | 再利用戦略 | 論文調査 |

### C3. MPC / 先進制御

| # | ギャップ | 必要性 | 調査方法 |
|---|---|---|---|
| C3.1 | **iPSC 浮遊灌流での MPC 定式化例** | Phase 2 シミュレータ設計 | 論文サーチ |
| C3.2 | **Manstein ODE を内部モデルとする MPC の実装パターン** | plant_model 拡張 | 技術調査（CasADi/do-mpc/acados） |
| C3.3 | **多変数 MPC（perfusion + agitation + DO）の計算コスト** | cadence 設計 | シミュレーション |
| C3.4 | **経済 MPC（Economic MPC）の導入条件** | Phase 3 最適化 | 文献サーチ |

### C4. PINN / ハイブリッドデジタルツイン

| # | ギャップ | 必要性 | 調査方法 |
|---|---|---|---|
| C4.1 | **iPSC 凝集体形成動力学の NN 構造** | Hybrid ODE+NN 設計 | 論文サーチ |
| C4.2 | **不確実性定量化手法の比較** | 信頼度スコア | 論文サーチ（GP/Deep Ensemble/Bayesian PINN/EFI） |
| C4.3 | **データ効率性（30 run 未満でも使える手法）** | R&D 早期導入 | 論文サーチ |
| C4.4 | **sim/real gap 縮小の評価指標** | モデル更新判断 | 文献調査 |

### C5. 凝集体画像・DL 品質代理指標

| # | ギャップ | 必要性 | 調査方法 |
|---|---|---|---|
| C5.1 | **label-free 画像特徴量と OCT4/SOX2/NANOG の定量的対応** | BO 品質項 | 論文サーチ＋実験 |
| C5.2 | **2D 画像解析モデルの凝集体転移効率** | 再利用戦略 | 論文サーチ |
| C5.3 | **at-line 自動セグメンテーション手法（U-Net/Mask R-CNN）** | 画像定量化 | 技術調査 |
| C5.4 | **DL 品質代理指標の BO 目的関数重み** | 多目的最適化 | 研究者ヒアリング＋感度分析 |

### C6. 規制・Annex 22

| # | ギャップ | 必要性 | 調査方法 |
|---|---|---|---|
| C6.1 | **Annex 22 最終文本・施行日** | GMP 移行計画 | 規制動向モニタリング |
| C6.2 | **BO/GP を「静的決定論的モデル」と見なせる規制解釈** | L2 分類 | 規制コンサル/ガイダンス |
| C6.3 | **GAMP5 AI Guide の実装マッピング** | カテゴリ分類 | ISPE ガイダンス |
| C6.4 | **職員独立性・dual control の R&D 軽量版** | ALCOA-lite | 規制動向 |

---

## 5. D. 検証・テストアセット

| # | アセット | 内容 | 優先度 | 備考 |
|---|---|---|---|---|
| D1 | plant_model golden test | 同一 actuators → 同一 sensors 軌道 | 最高 | `tests/test_plant_model.py` |
| D2 | Manstein 軌道テスト | 7 日 35×10⁶ cells/mL 再現 | 最高 | CI |
| D3 | L1 イベント網羅テスト | 全イベントに対する決定的応答を単体テスト | 高 | roadmap.md §2.1 #1 完了基準 |
| D4 | `validate_tool_call` テスト | 包絡線・ramp 制限違反の拒否 | 高 | |
| D5 | BO 再現性テスト | 固定シードで同じ提案 | 高 | static_deterministic_proof |
| D6 | 承認フロー E2E テスト | requested→approved→executed、タイムアウト | 高 | |
| D7 | ALCOA-lite 監査ログテスト | 全副作用ツールのログ取得 | 高 | 3+ run で確認 |
| D8 | MQTT 冪等性テスト | 重複コマンド拒否 | 中 | |
| D9 | 縮退運転テスト | ブレイン停止時の L0 維持 | 中 | |
| D10 | drift 監視テスト | 入力分布変化検知 | 低 | Phase 2 |

---

## 6. E. 規制・文書アセット

| # | アセット | 内容 | 優先度 | 備考 |
|---|---|---|---|---|
| E1 | Intended Use 文書テンプレート | L2 BO、将来 Raman PLS/画像 DL 用 | 高 | Annex 22 |
| E2 | モデルカードテンプレート | 訓練データ、性能限界、制約 | 高 | |
| E3 | 静的決定論的証明手順 | checksum、固定シード、再現性テスト | 高 | CI 統合 |
| E4 | データ分離設計 | train/valid/test/運用の分離 | 高 | |
| E5 | ALCOA-lite 監査ログスキーマ | who/when/what/why、承認履歴 | 高 | |
| E6 | EBR-like 実験プロビナンスレポート | 1 run = 1 report | 中 | R&D 一次 |
| E7 | プロンプトバージョニング手順 | L3 LLM の再現性 | 中 | |
| E8 | XAI/feature attribution 方針 | 各モデルタイプ別 | 低 | Phase 2 |
| E9 | ドリフト監視手順 | 入力分布・性能劣化 | 低 | Phase 2 |
| E10 | GMP 移行ギャップ分析 | R&D → GMP の差分 | 低 | Phase 3 |

---

## 7. F. インフラ・アーキテクチャアセット

| # | アセット | 内容 | 優先度 | 備考 |
|---|---|---|---|---|
| F1 | physical-ai-core 改修方針 | cognitive loop の常駐解除またはイベント駆動化 | 高 | ADR-0001 Follow-ups |
| F2 | event_store スキーマ | イベント・コマンド・承認・テレメトリの統一スキーマ | 高 | |
| F3 | audit_log 実装 | append-only + ハッシュチェーン | 高 | |
| F4 | `config/` ディレクトリ | 環境設定・包絡線・レシピ配置 | 高 | ROADMAP.md §2 不足点 |
| F5 | `infra/` ディレクトリ | gateway、virtual_edge、device_registry | 高 | ROADMAP.md §2 不足点 |
| F6 | ユーザー認証/ロール | 研究者/オペレータ/システム | 中 | |
| F7 | タイムスタンプ・NTP 同期 | ALCOA Contemporaneous | 中 | |
| F8 | オブジェクトストレージ接続 | 生データ・画像の WORM 保存 | 中 | |
| F9 | バックアップ/リストア | event_store の永続化 | 中 | |
| F10 | マルチバイオリアクタスケジューラ | 並行 run 管理 | 中 | FR-8 |

---

## 8. 不足アセットの優先度マトリクス

| 優先度 | 定義 | 該当アセット |
|---|---|---|
| **P0（最高）** | v1 閉ループを回すのに欠かせない | A1.1–A1.2, A2.1–A2.5, A3.1–A3.3, A6.1, B1.1–B1.2, B2.1–B2.4, B3.1–B3.5, D1–D4, E1–E6, F1–F5 |
| **P1（高）** | v1 品質・再現性に必須 | A1.3–A1.6, A4.1–A4.5, A6.4–A6.6, A7.1–A7.4, D5–D9 |
| **P2（中）** | Phase 2 以降の拡張基盤 | A2.6–A2.9, A5.1–A5.4, A7.5, B4.1, B4.4–B4.5, C1.2–C1.5, C2.1–C2.4, C3.1–C3.2, C5.3 |
| **P3（低）** | Phase 3 / 調査継続 | C1.1, C3.3–C3.4, C4.1–C4.4, C5.1–C5.2, C5.4, C6.1–C6.4, E7–E10, F6–F10 |

---

## 9. オンライン調査が特に必要なトピック

以下のトピックについては、先行事例・論文・概念を徹底的に調査し、実装計画に反映する。

1. **iPSC 浮遊灌流における MPC 定式化と実装パターン**（CasADi/do-mpc/acados）
2. **iPSC 固有の CPP 閾値・シア応答・凝集体品質相関**
3. **Raman 光散乱補正と iPSC 校正戦略**
4. **PINN / Hybrid ODE+NN のバイオプロセス適用事例と不確実性定量化**
5. **凝集体画像解析・DL 品質代理指標の iPSC 適用事例**
6. **PIC/S Annex 22 / GAMP5 AI Guide の R&D 軽量適用事例**

これらを Agent Swarm で並列調査し、`docs/design/closed_loop_planning/swarm_reports/` に個別レポートを残す。

---

## 10. 参照

- `docs/design/closed_loop_planning/01_roadmap_criticism_verification.md`
- `ROADMAP.md`
- `docs/design/roadmap.md`
- `docs/design/design_reconsideration_report.md`
- `docs/design/ground_knowledge/additional_investigation_integrated.md`
- `docs/design/ground_knowledge/integrated_report.md`
- `docs/design/kg_to_auto_cell.md`
- `docs/design/adr/0001-control-architecture.md`
