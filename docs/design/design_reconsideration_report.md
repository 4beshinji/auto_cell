# auto_cell A 層制御システム 設計再検討レポート

> **担当**: シニアアーキテクト（設計再検討エージェント）  
> **Date**: 2026-06-16  
> **Scope**: auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御、Manstein 型灌流 0→7 vvd）  
> **前提**: ADR-0001、requirements.md、kg_to_auto_cell.md、KG v2.1、Agent Swarm 産出物一式、ダウンロードレポート照合・追加調査統合レポート

---

## 1. Executive Summary（主要な結論と推奨）

本レポートは、Knowledge Graph v2.1（340 ノード/692 エッジ）および関連設計文書を精読し、現行設計（ADR-0001）を再検討したものである。

### 主要結論

1. **ADR-0001 の L0–L3 分離は妥当**〔事実：ADR-0001; KG `ctrl_split`, `loop`〕。秒オーダー安全ループを LLM 外に保ち、決定的コアを厚くする方針は、R&D 再現性・安全・Annex 22 対応の観点から維持すべきである。
2. **L1 を「決定的レシピ/ルールエンジン」とする判断は、v1（Phase 1）として最適**〔推定：ADR-0001; `recipe_executor`, `rule_engine`, `state_machine_l1`〕。MPC の導入可能性は v1 では却下せず、**将来拡張路線図（Phase 2/3）として明確に位置づける**べきである。
3. **L2 BO の探索空間・目的関数は未具体化**〔未確定：`bbo`, `safe_bo`, `batch_bo`, `multi_fidelity`〕。収量×生存率×多能性マーカー×凝集体適正サイズ×コストの多目的関数化、および重みの研究者合意が必要。
4. **L3 LLM の起動トリガーと権限は適切に制限されている**〔事実：`llm_orchestrator`, `human_approval`, `approval_workflow`〕。ただし、Annex 22 における「非クリティカル AI」としての位置づけを文書化すべき。
5. **CPP カタログは網羅的だが、閾値の「制限値/早期警戒値/トリガ値」の区別が不明確**〔推定：`cpp_glucose`, `cpp_lactate`, `cpp_osmolality`, `perfusion_trigger`, `ramp_limit`〕。CHO 由来数値の転用は既に排除されているが、アンモニア閾値の未確定性と凝集体径分布（>400 µm 割合）の追加が必要。
6. **観測性スタックは現実的**〔事実：`measurement_vcd_capacitance`, `measurement_atline_nova`, `measurement_aggregate_imaging`〕。in-line Raman を v1 オプションとする判断は妥当。ただし、品質/無菌の offline 限定は設計上の弱点であり、at-line 品質代理指標・rapid 無菌検知の調査をロードマップに入れるべき。
7. **デバイス IF（OPC-UA/LADS 第一・SiLA2 従・MQTT-native）は協業前提として現実的**〔事実：`opcua`, `lads_functional_unit`, `sila`, `gateway`〕。承認フローと MQTT request-response の整合は概ね成立するが、approval-state topic の明示が必要。
8. **規制・GMP 対応は「Annex 22-ready 骨格」を部分的に持つ**〔推定：`annex22`, `critical_ai`, `static_model`, `deterministic_output`, `alcoa`, `csv`, `part11`〕。R&D 一次で ALCOA-lite・監査ログ・CSV/CSA 軽量版を導入するコストは見合うが、完全 GMP 移行には電子署名・職員独立性・完全データ分離など大きなギャップが残る。
9. **技術ロードマップは現実的**〔推定：`mpc_roadmap_l1`, `raman_calibration_ipsc`, `hybrid_ode_nn`, `digital_twin`〕。v1/Phase2/Phase3 の機能分割を維持しつつ、未解決事項の優先順位と移行条件を具体化すべき。
10. **KG v2.1 の新規ノード（MPC、PINN、DT、Annex 22、XAI、Raman 校正等）を設計に反映する必要がある**〔推定：`mpc`, `pinn`, `digital_twin`, `annex22`, `xai`, `raman_calibration_ipsc`〕。特に `annex22 --constrains--> loop` / `llm_orchestrator` といったエッジは、L0/L1 の決定性と L3 の非クリティカル用途を設計で証明する必要がある。

### 推奨する変更の要約

| 優先度 | 変更 |
|---|---|
| **高** | ADR-0001 追記または ADR-0002 作成：MPC/PINN/DT の将来位置づけ、信頼度スコア層 |
| **高** | `kg_to_auto_cell.md` §4 CPP カタログ更新：制限値/警戒値/トリガ値の分離、アンモニア、凝集体分布、CSPR |
| **高** | 規制技術統制の追加：Intended Use 文書、データ分離、静的決定論的証明、XAI/信頼度スコア、ドリフト監視 |
| **中** | 技術ロードマップの具体化（v1/Phase2/Phase3 移行条件） |
| **中** | 観測性ロードマップ更新：offline 品質/無菌の弱点と at-line 代理指標・rapid 無菌検知の調査 |
| **中** | MQTT topic 契約に approval-state / HMI 通知 topic を追加 |
| **低** | README・追加調査レポートの相互参照更新 |

---

## 2. 現行設計の強み

1. **L0–L3 の厳格な分離**〔事実：ADR-0001; KG `ctrl_split`, `l0_local_pid`, `l0_fail_safe`〕
   - 安全クリティカルな高速ループ（pH/DO/温度/撹拌）を局所 PID に置き、ブレインは監督制御に限定。LLM を per-cycle 制御ループから外している。
   - ブレイン/通信断時も L0 が最終検証済 setpoint を保持し、培養を継続（NFR-S 遵守）。

2. **決定的制御コア + BO 探索層の分離**〔事実：ADR-0001; `recipe_executor`, `rule_engine`, `bbo`, `sdl`〕
   - run 内制御は決定的 DSL/ルールで、run 間最適化は BO。再現性（NFR-Rep）と探索効率（FR-5）を両立。
   - Tier2 `plant_model`（Manstein 2021 ベース 6 項 Monod ODE）が CSV/CSA 検証リグとして機能。

3. **Human-on-the-loop 承認モデル**〔事実：requirements.md FR-4; `human_approval`, `approval_workflow`〕
   - 包絡線外 setpoint・trigger_passage・BO 提案は研究者承認。タイムアウト時は安全側デフォルト。

4. **標準デバイス IF 選択**〔事実：`kg_to_auto_cell.md` §7; `opcua`, `lads_functional_unit`, `sila`, `gateway`〕
   - OPC-UA/LADS 第一、SiLA2 従、MQTT-native + gateway。産業標準・監査可能性・second-source を両立。

5. **観測性スタックの現実性**〔事実：`cpv`, `measurement_vcd_capacitance`, `measurement_atline_nova`, `measurement_aggregate_imaging`〕
   - v1 では in-line capacitance + at-line Nova + at-line 凝集体画像。Raman は iPSC 校正が未確定なためオプション/後段とする判断は合理的。

6. **KG v2.1 との整合性**〔推定：KG 全体〕
   - 新規ノード（MPC、PINN、DT、Annex 22、XAI、Raman 校正）が追加され、設計の拡張方向を裏付けている。

---

## 3. 発見した問題・矛盾・ギャップ

### 3.1 制御アーキテクチャ

| # | 問題 | 影響 | 根拠 |
|---|---|---|---|
| P1 | ADR-0001 は L1 = 決定的レシピ/ルールと決定したが、**MPC の将来位置づけが不明確** | Phase 2/3 ロードマップの欠如 | `alignment_with_downloaded_report.md` §5.1-1; `mpc`, `mpc_roadmap_l1` |
| P2 | L2 BO の探索空間・制約・目的関数が具体化されていない | 実装が着手できない | ADR-0001 Follow-ups; `bbo`, `safe_bo`, `batch_bo` |
| P3 | L3 LLM が「非クリティカル AI」として Annex 22 にどう分類されるか、文書化が不足 | 規制対応の曖昧さ | `annex22`, `noncritical_ai`, `generative_ai`, `llm_orchestrator` |
| P4 | 信頼度スコア層が設計に明示されていない | 低信頼度 AI 出力の HITL エスカレーションが未具体化 | `prediction_confidence_score`, `confidence_score`, `safe_bo` |

### 3.2 CPP / 制御変数カタログ

| # | 問題 | 影響 | 根拠 |
|---|---|---|---|
| P5 | **glucose/lactate/osmolality の「制限値」と「トリガ値/早期警戒値」が混同**している | L1 イベント閾値の誤設定リスク | `cpp_glucose`, `cpp_lactate`, `cpp_osmolality`, `perfusion_trigger` |
| P6 | アンモニアは監視値として扱われているが、**iPSC ネイティブ閾値が未確定** | イベント化/しない判断が曖昧 | `cpp_ammonia`, `add_cho_ipsc_ammonia_threshold` |
| P7 | 凝集体径は「平均径 150–350 µm」のみだが、**大径凝集体割合（>400 µm）の監視がない** | 壊死コア・品質低下の検出漏れ | `cpp_aggregate_diameter`, `add_aggimg_aggregate_size_pluripotency` |
| P8 | **Cell-Specific Perfusion Rate（CSPR）**が設計に現れていない | 培地利用効率と高密度安定性の最適化視点欠如 | `cpsr_control` |
| P9 | ramp 制限値（±0.5 vvd/30 min 等）が初期仮説のまま文献裏付けが弱い | シア/浸透圧ショック回避の根拠不足 | `ramp_limit` |

### 3.3 観測性スタック

| # | 問題 | 影響 | 根拠 |
|---|---|---|---|
| P10 | **品質マーカー（OCT4 等）・無菌性が offline/run 単位のみ** | run 内の品質劣化/汚染検知が遅延 | `monitoring_quality_offline`, `monitoring_sterility_offline` |
| P11 | in-line Raman の iPSC 校正戦略は調査済だが、設計文書への反映が不十分 | v1.5/v2 移行条件が不明確 | `raman_calibration_ipsc`, `raman_pls_model`, `raman_confidence_score` |
| P12 | 凝集体画像の「at-line 日次」という cadence が L1 イベント設計にどう組み込まれるか不明確 | リアルタイム性と画像遅延の整合 | `measurement_aggregate_imaging`, `add_aggimg_brightfield_atline` |

### 3.4 デバイス IF / LADS / SiLA2

| # | 問題 | 影響 | 根拠 |
|---|---|---|---|
| P13 | MQTT topic 契約に**承認状態（approval-state）や HMI 通知 topic** が明示されていない | 承認フローと telemetry の連携が弱い | `mqtt_topic_contract`, `gateway_cmd_ack`, `approval_workflow` |
| P14 | LADS Program/Result と EBR/`event_store` の対応は概念レベル | 実装時の ICD 具体化が不足 | `lads_program_result`, `ebr` |
| P15 | フォールバック梯子（LADS 不可時の OPC-UA custom/MQTT Sparkplug B/gRPC/REST）は設計されているが、**v1 でどこまで実装するか未定** | スコープ・コストの曖昧さ | `gateway`, `devprofile` |

### 3.5 規制・GMP 対応

| # | 問題 | 影響 | 根拠 |
|---|---|---|---|
| P16 | 「Annex 22-ready 骨格」と謳うが、**Intended Use 文書化・データ分離・職員独立性・静的決定論的証明**などの具体的技術的統制が未整備 | R&D 一次でも将来 GMP 移行時の再設計コスト増 | `annex22`, `static_deterministic_proof`, `data_segregation`, `staff_independence` |
| P17 | LLM/生成 AI を非クリティカル用途に限定する方針はあるが、**「クリティカル用途」の定義と境界**が文書化されていない | 誤用リスク | `critical_ai`, `noncritical_ai` |
| P18 | XAI/信頼度スコアの実装方針が L2 BO の GP 事後分散に留まり、**Raman PLS・画像 DL への適用**が未定 | Annex 22 の Explainability 要求への対応不足 | `xai`, `feature_attribution`, `raman_confidence_score`, `add_aggimg_human_approval_imaging` |

### 3.6 技術ロードマップ

| # | 問題 | 影響 | 根拠 |
|---|---|---|---|
| P19 | Phase 2/3 における **MPC・Raman 閉ループ・画像 DL 品質代理指標の移行条件**が数値化されていない | 段階移行の判断基準欠如 | `mpc_roadmap_l1`, `raman_calibration_ipsc`, `add_aggimg_aggregate_quality_proxy` |
| P20 | BO 目的関数の重み（収量 vs 多能性 vs コスト）が未決定 | L2 最適化の方向性が定まらない | `add_cho_ipsc_pluripotency_objective`, `qccrit` |

### 3.7 KG v2.1 活用

| # | 問題 | 影響 | 根拠 |
|---|---|---|---|
| P21 | KG 新規ノード（`mpc`, `pinn`, `digital_twin`, `annex22`, `xai`, `raman_calibration_ipsc` 等）が ADR/設計ブリッジに未反映 | KG と設計文書の乖離 | KG v2.1 全体 |
| P22 | `annex22 --constrains--> loop` / `llm_orchestrator` エッジに対し、設計がその制約を満たしていることを形式的に示していない | 規制トレーサビリティの欠如 | `annex22`, `loop`, `llm_orchestrator` |

---

## 4. 各観点での再評価

### 4.1 制御アーキテクチャの妥当性（§2.1）

#### L0–L3 分離
**評価**: 適切。〔事実：ADR-0001; KG `ctrl_split`, `l0_local_pid`, `l0_fail_safe`〕

- L0（局所 PID）は温度/pH/DO/撹拌の高速安全ループを担い、L1（決定的レシピ/ルール）は 30 s+ / イベント駆動の監督制御を担う。
- LLM は L3 に配置され、per-cycle 制御から排除されている。
- ブレイン停止時も L0/L1 が縮退運転する構造は NFR-S（安全）・NFR-R（可用性）を満たす。

#### L1 を「決定的レシピ/ルールエンジン」とする判断
**評価**: v1 として最適。ただし MPC 導入可能性を将来拡張として明記すべき。〔推定：ADR-0001; `recipe_executor`, `rule_engine`, `mpc`, `mpc_vs_rule_engine`〕

- R&D 一次では run 内プロセスは既知レシピ（Manstein: 灌流 0→7 vvd・固定設定点・条件起動給餌）の決定的実行が大半。
- LLM per-cycle 推論は再現性・安全・コストで不利。
- 一方、ダウンロードレポートは MPC を CHO fed-batch で実用化（抗体タイトル 2% 向上）と報告しており、iPSC 灌流プロセスでも **perfusion rate の制約付き最適化**に MPC が有効な可能性がある〔`mpc_ipsc_perfusion`, `mpc_lactate_feedback`, `dynamic_perfusion_ipsc`〕。
- 結論：v1 はルールエンジンのまま、Phase 2 から plant_model ベース MPC シミュレーション、Phase 3 で多変数適応 MPC を検討。

#### L2 BO の探索空間・制約・目的関数
**評価**: 方向性は正しいが具体化が不足。〔未確定：`bbo`, `safe_bo`, `batch_bo`, `multi_fidelity`, `add_cho_ipsc_pluripotency_objective`〕

- 探索空間の候補：seeding_density、initial_glucose、perfusion_ramp_profile、max_perfusion_rate、agitation_base_rpm、DO transition、Y-27632 濃度等。
- 制約：CPP 包絡線（Manstein 2021）、pump ramp 制限、凝集体シア上限。
- 目的関数：収量（VCD_final）× 生存率 × 未分化マーカー陽性率（OCT4/SOX2/NANOG/SSEA/TRA）× 凝集体適正サイズ比率 × コスト。重みは細胞株・用途で変動〔`add_cho_ipsc_pluripotency_objective`, `add_cho_ipsc_qc_marker_panel`〕。
- 多忠実度：Tier2 `plant_model` を低忠実度、実 run を高忠実度。

#### L3 LLM の起動トリガーと権限
**評価**: 過剰ではなく、むしろ保守的。ただし Annex 22 分類を明示すべき。〔推定：`llm_orchestrator`, `human_approval`, `approval_workflow`, `annex22`, `noncritical_ai`〕

- トリガー：承認要求仲介、曖昧知覚解釈（画像異常等）、新規例外対応提案、研究者対話、BO 結果説明。
- 権限：包絡線検証・変化率制限は決定的 sanitizer が行い、LLM は提案・説明のみ。
- Annex 22 では生成 AI/LLM はクリティカル用途で禁止、非クリティカル用途でも HITL 必須。現行設計はこの条件を満たす。

### 4.2 CPP / 制御変数カタログの妥当性（§2.2）

#### 12 変数の網羅性
**評価**: v1 として網羅的。ただし監視変数・分布指標の追加が望ましい。〔推定：`kg_to_auto_cell.md` §4; KG `cpp_*`〕

- 現行 12 変数（pH, DO, temp, agitation, lactate, glucose, glutamine, osmolality, aggregate diameter, VCD, perfusion rate, sterility）は A 層制御に必要な要素をカバー。
- 追加すべき：
  - **ammonia**: 監視値（iPSC 閾値未確定）〔`cpp_ammonia`, `add_cho_ipsc_ammonia_threshold`〕
  - **viability**: BO 目的関数入力〔`cpp_viability`〕
  - **凝集体径分布**: 平均径だけでなく大径凝集体割合（>400 µm）〔`cpp_aggregate_diameter`, `add_aggimg_aggregate_size_pluripotency`〕
  - **CSPR**: 培地利用効率指標〔`cpsr_control`〕

#### CHO 由来数値の転用
**評価**: 既存設計は転用を排除しているが、文書化を強化すべき。〔事実：`alignment_with_downloaded_report.md` §5.3; `add_cho_ipsc_transfer_caution`, `add_cho_ipsc_cpp_reinterpretation`〕

- 乳酸閾値、アンモニア閾値、浸透圧上限、攪拌 rpm、灌流率、mAb タイトル目的関数は iPSC にそのまま転用不可。

#### トリガ閾値と制限値の区別
**評価**: 不十分。以下のように整理すべき。〔推定：`cpp_glucose`, `cpp_lactate`, `cpp_osmolality`, `perfusion_trigger`〕

| CPP | 制限値（Limit） | 早期警戒値（Warning） | 備考 |
|---|---|---|---|
| Glucose | > 1.5 mM（K_Glc） | 1.8 mM（運用マージン） | 制限値は Manstein 2021 Table 1 |
| Lactate | < 50 mM（K_Lac） | 35 mM（早期警戒） | 制限値は Manstein 2021 Table 1 |
| Osmolality | < 500 mOsm/kg（K_Osm） | 450 mOsm/kg（早期警戒） | 制限値は Manstein 2021 Table 1 |

#### 凝集体径 150–350 µm
**評価**: 初期仮説として適切だが、細胞株依存で再校正が必要。〔推定：`cpp_aggregate_diameter`; `add_aggimg_aggregate_size_pluripotency`, `add_aggimg_src_borys_2021`, `add_aggimg_src_stemcell_mtesr3d`〕

- Borys 2021 では >400 µm で壊死リスク。平均径 150–350 µm に加え、大径凝集体割合を監視。
- STEMCELL mTeSR 3D マニュアルでは理想平均径 50–200 µm とする一方、Manstein/Borys 系では大きめ。細胞株・培地・攪拌形状で再校正。

### 4.3 観測性スタックの現実性（§2.3）

#### in-line Raman を v1 オプションとする判断
**評価**: 妥当。〔推定：`measurement_raman_inline`, `raman_calibration_ipsc`, `raman_cho_to_ipsc_transfer`〕

- CHO/mAb では TRL 8-9 だが、iPSC 浮遊凝集体では実証が限定的。
- 凝集体・高密度細胞による光散乱（Mie 散乱）が PLS 精度を低下させる〔`raman_cell_scattering`, `raman_aggregate_interference`〕。
- v1 では Nova FLEX2 を正解ラベルとした校正計画を策定し、Raman 値は記録・表示のみ。

#### Nova FLEX2 + capacitance + at-line 画像の v1 スタック
**評価**: 実行可能。〔事実：`measurement_vcd_capacitance`, `measurement_atline_nova`, `measurement_aggregate_imaging`〕

- capacitance VCD は Manstein iPSC で定性的一致が確認されている。
- Nova FLEX2 は産業標準 at-line analyzer。
- at-line 凝集体画像は Kropp 2019 等の先行例あり、日次運用が現実的。

#### 品質/無菌の offline 限定
**評価**: 設計上の弱点。〔推定：`monitoring_quality_offline`, `monitoring_sterility_offline`〕

- run 内での品質劣化/汚染検知が遅延し、リアクティブな対応に限られる。
- 対策：at-line 凝集体画像からの品質代理指標、rapid micro/ATP 検知等の調査を Phase 2 ロードマップに入れる。

### 4.4 デバイス IF / LADS / SiLA2（§2.4）

#### OPC-UA/LADS 第一の判断
**評価**: 協業前提として現実的。〔事実：`opcua`, `lads_functional_unit`, `lads_sensor_function`, `lads_controller_function`, `lads_actuator_function`〕

- LADS v1.0.0 はバイオリアクタを Functional Unit × Function で明示モデル化。
- `channel_config` ↔ LADS sensor Function、`tool_schemas` ↔ LADS controller/actuator Function(method)、`event_store` ↔ LADS Program/Result の対応が自然。

#### MQTT topic 設計と承認フローの request-response
**評価**: 整合しているが、approval-state topic の追加が必要。〔事実：`mqtt_topic_contract`, `gateway_cmd_ack`, `approval_workflow`〕

- 現行 topic: `cell/{culture_unit_id}/{direction}/{category}/{device_id}/{function_id}`
- 追加提案: `cell/{cu}/state/approval/{request_id}` および `cell/{cu}/notify/hmi/{priority}` で承認状態と HMI 通知を分離。

### 4.5 規制・GMP 対応（§2.5）

#### Annex 22-ready 骨格
**評価**: 部分的に持っているが、技術的統制の具体化が必要。〔推定：`annex22`, `critical_ai`, `static_model`, `deterministic_output`, `dynamic_model`, `probabilistic_model`, `generative_ai`〕

- L0/L1 は決定的制御器 → Annex 22 のクリティカル AI 定義に該当せず、または明示的ルールとして許容。
- L2 BO/GP は「訓練データ固定・シード固定」で静的モデルとして扱える可能性があるが、規制当局の解釈が未確定〔`static_deterministic_proof`〕。
- L3 LLM は非クリティカル用途に限定。

#### ALCOA-lite・監査ログ・CSV/CSA
**評価**: R&D 一次で導入コストは見合う。〔推定：`alcoa`, `audit`, `csv`, `part11`, `ebr`〕

- 全副作用ツール呼び出しの不変ログ、timestamp、correlation ID、承認履歴は R&D 再現性にも必須。
- ただし完全電子署名・WORM・職員独立性・IQ/OQ/PQ は GMP 移行時の課題として設計境界に明記。

### 4.6 技術ロードマップ（§2.6）

#### v1/Phase2/Phase3 の機能分割
**評価**: 現実的だが、移行条件を数値化すべき。〔推定：`additional_investigation_integrated.md` §8〕

| フェーズ | 現行計画 | 推奨追加 |
|---|---|---|
| v1 / Phase 1 | L1 ルール、Manstein ODE、Nova、at-line 画像、ALCOA-lite | Raman 校正計画、意図用途文書テンプレート |
| Phase 2 | plant_model 拡張、多忠実度 BO | MPC シミュレーション、Raman アドバイザリ、画像定量化、静的決定論的証明 |
| Phase 3 | Hybrid ODE+NN、DT | 多変数適応 MPC、Raman 閉ループ、DL 品質代理指標、GMP IQ/OQ/PQ |

#### 未解決事項の優先順位
**評価**: 概ね適切だが、BO 目的関数重みと承認タイムアウト値は v1 実装前に解決すべき。〔推定：`additional_investigation_integrated.md` §9〕

### 4.7 KG v2.1 の活用（§2.7）

#### 新規追加ノードの設計反映
**評価**: 反映が必要。〔推定：KG v2.1 全体〕

| 新規ノード群 | 設計への反映 |
|---|---|
| `mpc`, `mpc_ipsc_perfusion`, `mpc_roadmap_l1` | ADR/ロードマップへの将来拡張記述 |
| `pinn`, `digital_twin`, `hybrid_ode_nn`, `multifidelity_pinn` | plant_model 拡張路線、L2 BO 低忠実度モデル |
| `annex22`, `critical_ai`, `static_model`, `deterministic_output` | 規制技術統制、L0/L1 決定性証明 |
| `xai`, `confidence_score`, `feature_attribution` | 信頼度スコア層、HITL エスカレーション |
| `raman_calibration_ipsc`, `raman_pls_model`, `raman_confidence_score` | Raman 導入ロードマップ、光散乱補正 |
| `add_cho_ipsc_*` | CHO→iPSC 非転用の設計原則強化 |
| `add_aggimg_*` | 凝集体画像解析ロードマップ |

#### エッジ整合性の検証
**評価**: 整合しているが、設計文書への反映が必要。〔推定：KG v2.1 edges〕

- `annex22 --constrains--> loop`: L0/L1 の決定性で充足。
- `annex22 --constrains--> llm_orchestrator`: L3 を非クリティカル用途に限定することで充足。
- `pinn --researches--> loop` / `hybrid_ode_nn --extends--> tier2_plant_model`: Phase 3 拡張として反映。
- `raman_calibration_ipsc --calibrates--> measurement_raman_inline`: v1.5/v2 移行条件として反映。

---

## 5. 推奨する設計変更（優先度付き）

### 5.1 優先度：高

#### C1. ADR-0001 追記または ADR-0002 作成：将来制御層の位置づけ
- **対象**: `docs/design/adr/0001-control-architecture.md`（追記）または新規 `docs/design/adr/0002-future-control-layers.md`
- **変更内容**:
  - MPC を L1 の将来拡張として位置づける（Phase 2: シミュレーション、Phase 3: 多変数適応 MPC）。
  - PINN/DT/Hybrid ODE+NN を plant_model/L2 BO 低忠実度モデルの拡張として位置づける。
  - 信頼度スコア層（`prediction_confidence_score`, `confidence_score`）を L2/L3 と HMI の間に追加。
  - すべて将来技術は Human-on-the-loop 承認を必須とすることを明記。
- **理由**: ダウンロードレポートとの整合、KG v2.1 新規ノード反映、Annex 22 対応。〔`mpc`, `mpc_roadmap_l1`, `pinn`, `digital_twin`, `hybrid_ode_nn`, `prediction_confidence_score`, `annex22`〕
- **KG ノード**: `mpc`, `pinn`, `digital_twin`, `hybrid_ode_nn`, `prediction_confidence_score`, `annex22`, `human_approval`

#### C2. `kg_to_auto_cell.md` §4 CPP カタログ更新
- **対象**: `docs/design/kg_to_auto_cell.md` §4
- **変更内容**:
  - 各 CPP に「目標値/制限値/早期警戒値/トリガ値」を明確に区分。
  - アンモニアを監視値として追加（iPSC 閾値未確定）。
  - 凝集体径に「大径凝集体割合（>400 µm）」の代理指標を追加。
  - CSPR（Cell-Specific Perfusion Rate）の概念を追加。
  - ramp 制限値を「初期仮説」として明示し、実機校正を必須とする注記を追加。
- **理由**: 閾値混同による誤動作防止、品質リスク低減。〔`cpp_glucose`, `cpp_lactate`, `cpp_osmolality`, `cpp_ammonia`, `cpp_aggregate_diameter`, `cpsr_control`, `ramp_limit`, `perfusion_trigger`〕
- **KG ノード**: `cpp_*`, `cpsr_control`, `ramp_limit`, `perfusion_trigger`, `add_cho_ipsc_ammonia_threshold`, `add_aggimg_aggregate_size_pluripotency`

#### C3. 規制技術統制の追加
- **対象**: `docs/design/kg_to_auto_cell.md` §5、新規 `docs/design/regulatory_technical_controls.md`
- **変更内容**:
  - Intended Use 文書化テンプレート（L2 BO、将来の Raman PLS/画像 DL 用）。
  - データ分離（train/valid/test/運用）と職員独立性（dual control/4-eyes 緩和）。
  - 静的決定論的証明（チェックサム・固定シード・再現性テスト・モデルカード）。
  - XAI/信頼度スコア（GP 事後分散、PLS Q 残差/Hotelling T²、DL 予測不確実性）。
  - ドリフト監視（入力分布・性能劣化）。
  - L3 LLM の非クリティカル用途限定とプロンプトバージョニング。
- **理由**: Annex 22-ready 骨格を実質化。〔`annex22`, `critical_ai`, `static_model`, `deterministic_output`, `xai`, `confidence_score`, `feature_attribution`, `drift_monitoring`, `test_data_independence`, `staff_independence`, `data_segregation`, `static_deterministic_proof`, `gamp_ai_lifecycle`〕
- **KG ノード**: `annex22`, `static_deterministic_proof`, `data_segregation`, `staff_independence`, `xai`, `confidence_score`, `drift_monitoring`, `gamp_ai_lifecycle`

### 5.2 優先度：中

#### C4. 技術ロードマップの具体化
- **対象**: 新規 `docs/design/roadmap.md` または `docs/design/ground_knowledge/integrated_report.md` 更新
- **変更内容**:
  - v1/Phase2/Phase3 の機能一覧に加え、各フェーズの**移行条件**を数値化（run 蓄積数、校正バッチ数、性能閾値等）。
  - Phase 2: 30+ run 蓄積、MPC シミュレーション、Raman 5+ バッチ校正、画像定量化。
  - Phase 3: 50–100+ run 蓄積、多変数 MPC、Raman 閉ループ、DL 品質代理指標。
- **理由**: 段階的投資とリスク管理。〔`mpc_roadmap_l1`, `raman_calibration_ipsc`, `add_aggimg_aggregate_quality_proxy`, `data_requirement_pinn`〕
- **KG ノード**: `mpc_roadmap_l1`, `raman_calibration_ipsc`, `hybrid_ode_nn`, `digital_twin`, `add_aggimg_aggregate_quality_proxy`

#### C5. 観測性ロードマップ更新
- **対象**: `docs/design/kg_to_auto_cell.md` §4.2
- **変更内容**:
  - offline 品質/無菌の弱点を明記。
  - Phase 2 で at-line 凝集体画像品質代理指標、rapid micro/ATP 無菌検知の調査を追加。
  - Raman 導入段階（v1 観測→v1.5 アドバイザリ→v2 閉ループ）を設計に反映。
- **理由**: run 内品質リスクの低減。〔`monitoring_quality_offline`, `monitoring_sterility_offline`, `raman_calibration_ipsc`, `add_aggimg_aggregate_quality_proxy`〕
- **KG ノード**: `measurement_*`, `raman_calibration_ipsc`, `add_aggimg_aggregate_quality_proxy`

#### C6. MQTT topic 契約に approval-state / HMI 通知 topic を追加
- **対象**: `docs/design/kg_to_auto_cell.md` §7.3、§8
- **変更内容**:
  - `cell/{culture_unit_id}/state/approval/{request_id}`: 承認要求の状態遷移（requested/approved/rejected/pending_timeout/executed/cancelled）。
  - `cell/{culture_unit_id}/notify/hmi/{priority}`: HMI 通知（P0–P3）。
  - `cmd`/`ack` と approval-state topic の correlation 方法を明記。
- **理由**: 承認フローと telemetry の一貫性。〔`mqtt_topic_contract`, `gateway_cmd_ack`, `approval_workflow`〕
- **KG ノード**: `mqtt_topic_contract`, `gateway_cmd_ack`, `approval_workflow`, `human_approval`

### 5.3 優先度：低

#### C7. CHO→iPSC 非転用の設計原則強化
- **対象**: `docs/design/kg_to_auto_cell.md` §4.1 または新規 `docs/design/cho_ipsc_transfer_caution.md`
- **変更内容**: CHO 由来数値・目的関数・戦略を iPSC にそのまま転用しないことを設計原則として強調。
- **理由**: ダウンロードレポート（CHO/mAb 中心）との混同防止。〔`add_cho_ipsc_transfer_caution`, `add_cho_ipsc_cpp_reinterpretation`〕
- **KG ノード**: `add_cho_ipsc_transfer_caution`, `add_cho_ipsc_cpp_reinterpretation`

#### C8. README と追加調査レポートの相互参照更新
- **対象**: `README.md`、`docs/design/additional_tasks_memo.md`
- **変更内容**: ロードマップと規制技術統制への参照を追加。
- **理由**: 設計文書間の一貫性。〔—〕
- **KG ノード**: —

---

## 6. 更新すべき設計文書一覧

| # | 文書パス | 更新内容 |
|---|---|---|
| 1 | `docs/design/adr/0001-control-architecture.md` | MPC/PINN/DT/信頼度スコア層の将来位置づけを追記 |
| 2 | `docs/design/kg_to_auto_cell.md` §4 | CPP カタログ：制限値/警戒値/トリガ値の区分、アンモニア、凝集体分布、CSPR |
| 3 | `docs/design/kg_to_auto_cell.md` §4.2 | 観測性スタック：offline 品質/無菌の弱点、Raman 導入段階 |
| 4 | `docs/design/kg_to_auto_cell.md` §5 | 規制技術統制：Annex 22 対応 5 本柱の反映 |
| 5 | `docs/design/kg_to_auto_cell.md` §7.3 / §8 | MQTT topic 契約に approval-state / HMI 通知 topic を追加 |
| 6 | 新規 `docs/design/adr/0002-future-control-layers.md`（任意） | MPC/PINN/DT/信頼度スコアの詳細設計 |
| 7 | 新規 `docs/design/regulatory_technical_controls.md` | Annex 22-ready 技術的統制の詳細 |
| 8 | 新規 `docs/design/roadmap.md` | v1/Phase2/Phase3 移行条件を数値化したロードマップ |
| 9 | `README.md` | ロードマップ・規制対応への参照追加 |
| 10 | `docs/design/additional_tasks_memo.md` | 完了済み調査と未解決事項の更新 |

---

## 7. 次のステップ・アクション

### 即時（1–2 週間）

1. **BO 目的関数の重みを研究者と合意**（U4）。影響：L2 最適化方向。〔`add_cho_ipsc_pluripotency_objective`〕
2. **承認タイムアウト値の初期値を設定**（U5）。影響：HMI/ワークフロー。〔`approval_workflow`〕
3. **レシピ DSL の正式文法を策定**（U3）。影響：L1 実装。〔`recipe_dsl`〕
4. **core の cognitive-loop 改修方針を確定**（U4）。影響：L1/L3 実装。〔`loop`, `llm_orchestrator`〕

### 短期（1–3 ヶ月）

5. **C1（ADR 追記/新規）を実施**。MPC/PINN/DT/信頼度スコア層の設計位置づけ。
6. **C2（CPP カタログ更新）を実施**。制限値/警戒値/トリガ値の区分。
7. **C3（規制技術統制）を実施**。Intended Use テンプレート、データ分離設計。
8. **C6（MQTT topic 更新）を実施**。approval-state / HMI 通知 topic。

### 中期（3–12 ヶ月）

9. **C4/C5（ロードマップ・観測性）を実施**。
10. **Tier2 plant_model ODE 実装とゴールデンテスト作成**。
11. **HMI UX プロトタイプの研究者フィードバック収集**。
12. **event_store/audit/approval フローの PoC**。

### 継続

13. **Raman chemometric モデルの iPSC 校正実験計画**。
14. **online/rapid 無菌検知手段の調査**。
15. **Annex 22 最終文本・施行日のモニタリング**。

---

## 8. トレーサビリティ（KG ノード ID との対応）

### 8.1 制御アーキテクチャ

| 設計要素 | KG ノード ID |
|---|---|
| L0 局所 PID | `l0_local_pid` |
| L0 フェイルセーフ | `l0_fail_safe` |
| L1 決定的レシピ実行器 | `recipe_executor` |
| L1 ルールエンジン | `rule_engine` |
| L1 状態機械 | `state_machine_l1` |
| L2 バッチ BO | `bbo`, `batch_bo` |
| L2 制約付き/Safe BO | `safe_bo` |
| L2 多忠実度 BO | `multi_fidelity`, `multifidelity_pinn` |
| L3 LLM オーケストレータ | `llm_orchestrator` |
| Human-on-the-loop 承認 | `human_approval`, `approval_workflow` |
| MPC 将来拡張 | `mpc`, `mpc_ipsc_perfusion`, `mpc_roadmap_l1` |
| PINN/DT 将来拡張 | `pinn`, `digital_twin`, `hybrid_ode_nn` |
| 信頼度スコア | `prediction_confidence_score`, `confidence_score` |

### 8.2 CPP / 制御変数

| 設計要素 | KG ノード ID |
|---|---|
| pH | `cpp_ph` |
| DO | `cpp_do` |
| 温度 | `cpp_temp` |
| 撹拌 | `cpp_agitation` |
| グルコース | `cpp_glucose` |
| 乳酸 | `cpp_lactate` |
| グルタミン | `cpp_glutamine` |
| 浸透圧 | `cpp_osmolality` |
| アンモニア | `cpp_ammonia` |
| 凝集体径 | `cpp_aggregate_diameter` |
| VCD | `cpp_vcd` |
| 生存率 | `cpp_viability` |
| 灌流率 | `cpp_perfusion_rate` |
| 灌流トリガ | `perfusion_trigger` |
| Ramp 制限 | `ramp_limit` |
| CSPR | `cpsr_control` |

### 8.3 観測性

| 設計要素 | KG ノード ID |
|---|---|
| in-line capacitance VCD | `measurement_vcd_capacitance` |
| in-line Raman | `measurement_raman_inline` |
| at-line Nova FLEX2 | `measurement_atline_nova` |
| at-line 凝集体画像 | `measurement_aggregate_imaging` |
| FBRM CLD | `measurement_fbrm_cld` |
| Ovizio D3HM | `measurement_ovizio_dhm` |
| Raman 校正戦略 | `raman_calibration_ipsc`, `raman_pls_model` |
| Raman 光散乱 | `raman_cell_scattering`, `raman_aggregate_interference` |
| 凝集体品質代理指標 | `add_aggimg_aggregate_quality_proxy` |

### 8.4 デバイス IF

| 設計要素 | KG ノード ID |
|---|---|
| OPC-UA/LADS | `opcua`, `lads_functional_unit` |
| LADS sensor Function | `lads_sensor_function` |
| LADS controller Function | `lads_controller_function` |
| LADS actuator Function | `lads_actuator_function` |
| LADS Program/Result | `lads_program_result` |
| SiLA2 | `sila`, `sila_feature` |
| Gateway | `gateway` |
| MQTT topic 契約 | `mqtt_topic_contract` |
| Gateway cmd/ack | `gateway_cmd_ack` |
| ICD setpoint envelope | `icd_setpoint_envelope` |

### 8.5 規制・GMP

| 設計要素 | KG ノード ID |
|---|---|
| PIC/S GMP Annex 22 | `annex22` |
| クリティカル AI | `critical_ai` |
| 非クリティカル AI | `noncritical_ai` |
| 静的モデル | `static_model` |
| 決定論的出力 | `deterministic_output` |
| 生成 AI | `generative_ai` |
| HITL | `hitl` |
| XAI | `xai` |
| 信頼度スコア | `confidence_score` |
| 特徴量帰属 | `feature_attribution` |
| ドリフト監視 | `drift_monitoring` |
| データ分離 | `data_segregation` |
| 職員独立性 | `staff_independence` |
| 静的決定論的証明 | `static_deterministic_proof` |
| ALCOA+ | `alcoa` |
| CSV/CSA | `csv` |
| Part11 | `part11` |
| EBR | `ebr` |
| 監査証跡 | `audit` |

### 8.6 CHO → iPSC 転換

| 設計要素 | KG ノード ID |
|---|---|
| CHO 代謝プロファイル | `add_cho_ipsc_cho_metabolism` |
| iPSC 代謝プロファイル | `add_cho_ipsc_ipsc_metabolism` |
| 高解糖性シフト | `add_cho_ipsc_glycolytic_shift` |
| 乳酸閾値の細胞種差 | `add_cho_ipsc_lactate_threshold` |
| アンモニア閾値の未確定性 | `add_cho_ipsc_ammonia_threshold` |
| 浸透圧閾値の細胞種差 | `add_cho_ipsc_osmolality_threshold` |
| グルコース閾値の細胞種差 | `add_cho_ipsc_glucose_threshold` |
| 凝集体内酸素拡散限界 | `add_cho_ipsc_aggregate_oxygen_diffusion` |
| 凝集体サイズを CPP として扱う | `add_cho_ipsc_aggregate_size_cpp` |
| iPSC シア感受性 | `add_cho_ipsc_shear_sensitivity` |
| CHO mAb タイトル目的関数 | `add_cho_ipsc_mab_titer_objective` |
| iPSC 多能性品質目的関数 | `add_cho_ipsc_pluripotency_objective` |
| 転用注意 | `add_cho_ipsc_transfer_caution` |

---

## 出典・参照

| ID | タイトル | パス/URL |
|---|---|---|
| ADR-0001 | Control architecture — thin LLM orchestrator over deterministic tools + Bayesian optimization | `docs/design/adr/0001-control-architecture.md` |
| requirements | auto_cell A 層 制御システム 要求仕様 | `docs/design/requirements.md` |
| kg_bridge | KG → auto_cell 設計ブリッジ | `docs/design/kg_to_auto_cell.md` |
| integrated_report | auto_cell A 層統合設計根拠レポート | `docs/design/ground_knowledge/integrated_report.md` |
| alignment | ダウンロードレポートと auto_cell 設計方向性の照合分析 | `docs/design/alignment_with_downloaded_report.md` |
| additional_integrated | 追加調査統合レポート | `docs/design/ground_knowledge/additional_investigation_integrated.md` |
| KG v2.1 | iPS自動培養ソフトウェア ドメイン知識マップ v2.1 | `docs/knowledge_graph/knowledge_graph_v2_1.json` |
| Manstein 2021 | Manstein & Zweigerdt 2021, Stem Cells Transl Med / STAR Protocols | DOI 10.1002/sctm.20-0453; PMC8666714 |
| Borys 2021 | Borys et al. 2021, Stem Cell Res Ther 12:55 | PMC7805206 |
| Annex 22 draft | EudraLex Volume 4 — Draft Annex 22: Artificial Intelligence (July 2025) | `src_pics_annex22_draft` |

---

*本レポートは A 層（iPSC 浮遊/凝集体バイオリアクター制御）に限定。樹立/分化/双腕/接着 conf は設計境界として参照のみ。全主張には事実/推定/未確定/設計判断のいずれかを付与し、KG ノード ID との対応を示した。*
