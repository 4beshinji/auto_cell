# A 層 CPP / 制御変数カタログ（Mode A: 設計根拠レポート）

> Agent: `agent_cpp_catalog`  
> Scope: auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御、Manstein 型灌流 0→7 vvd、目標密度 ~35×10⁶ cells/mL）  
> Architecture: ADR-0001（L0 局所 PID + L1 決定的レシピ/ルール + L2 ベイズ最適化 + L3 薄い LLM オーケストレータ）  
> Human-on-the-loop: 包絡線内アクションは自律、包絡線外/重大アクションは承認。

---

## 0. エグゼクティブサマリ

本書は A 層の全 Critical Process Parameter（CPP）をカタログ化し、数値の根拠、制御対象者、イベント、変化率制限（ramp）、未確定項目を整理した設計根拠集である。原典は **Manstein & Zweigerdt 2021**（Stem Cells Transl Med / STAR Protocols）であり、Tier2 `plant_model` の 6 定数および検証軌道（7 日 35×10⁶ cells/mL、DO 40%→10%、pH 7.1）は原典と一致している〔事実〕。

A 層の主制御レバーは **灌流/給餌率（0→7 vvd）** であり、これが glucose 供給と lactate/osmolality 希釈を一手に握る。凝集体径・撹拌・DO/pH 設定点・継代トリガを補助レバーとする。品質（未分化/同一性）と無菌性は offline/run 単位で BO 目的関数側に位置づけ、L1 決定的制御の直接対象外とする〔設計境界〕。

---

## 1. 用語定義

| 用語 | 定義 |
|---|---|
| **設定点（setpoint）** | L0 局所 PID または L1 監督制御が維持しようとする目標値。 |
| **制限値（limit）** | `validate_tool_call`/sanitizer で厳守する包絡線の上下限。超過は承認要求または禁止。 |
| **目標値（target）** | 培養最終状態で到達すべき値（例: VCD ~35×10⁶ cells/mL）。BO 目的関数の入力。 |
| **トリガ値（trigger）** | 条件起動アクション（灌流 ramp up、サンプリング、継代）を発火する閾値。 |
| **ramp 制限** | 単位時間あたりのアクチュエータ変化率上限。シアストレス・浸透圧ショック回避。 |

---

## 2. CPP 一覧表

### 2.1 物理・環境 CPP（L0 局所 PID 主体、L1 設定点変更可）

| 変数名 | 目標/範囲 | channel | actuator / tool | イベント | 根拠 | 不確実性 |
|---|---|---|---|---|---|---|
| `ph` | **7.1**（設定点） | in-line pH probe | `set_gas_setpoint(CO₂/base)` | `ph_out_of_range` | Manstein 2021: pH 7.1 で灌流培養運転〔事実〕。 | 機器校正 2 点標準、目標帯 ±0.1 は実装仮定〔推定〕。 |
| `do` | **40 % → 10 %**（設定点） | in-line DO probe | `set_gas_setpoint(DO)` + `set_agitation_rpm` カスケード | `do_low` | Manstein 2021: DO 40%（低密度）→ day 6-7 で 10% まで低下〔事実〕。 | 高密度化に伴う自然低下を許容、10% 未満は警告閾値〔推定〕。 |
| `temp` | **37 ℃**（設定点） | in-line temp probe | heater / thermal jacket | `temp_out_of_range` | 標準哺乳動物細胞培養温度〔事実〕。 | ±0.2 ℃ 程度は装置依存〔推定〕。 |
| `agitation_rpm` | **50–120 rpm**（範囲） | tachometer / LADS Function | `set_agitation_rpm` | `shear_risk` | Borys 2021: Vertical-Wheel で最適 40 rpm、50–120 rpm は auto_cell の上限包絡線〔事実/設計選択〕。 | 最適域 40–60 rpm で運転、120 rpm は稀〔推定〕。 |

### 2.2 代謝 CPP（L1 監督制御の主レバー：灌流/給餌）

| 変数名 | 目標/範囲 | channel | actuator / tool | イベント | 根拠 | 不確実性 |
|---|---|---|---|---|---|---|
| `glucose` | **> 1.5 mM**（制限値/トリガ） | in-line Raman or at-line Nova FLEX2 | `set_perfusion_rate` / `feed` | `glucose_low` | Manstein 2021 Table 1: K_Glc = 1.5 mM〔事実〕。 | in-line Raman は CHO 実証、iPSC 再校正必須〔推定〕。 |
| `lactate` | **< 50 mM**（制限値） | in-line Raman or at-line Nova FLEX2 | `set_perfusion_rate` / `exchange_media` | `lactate_high` | Manstein 2021 Table 1: K_Lac = 50 mM〔事実〕。 | 同上。 |
| `glutamine` | **> 0.01 mM**（制限値） | in-line Raman or at-line Nova FLEX2 | `feed` | `glutamine_low` | Manstein 2021 Table 1: K_Gln = 0.01 mM〔事実〕。 | 同上。 |
| `osmolality` | **< 500 mOsm/kg**（制限値） | at-line Nova FLEX2 / 推定 | `set_perfusion_rate` / `exchange_media` | `osmolality_high` | Manstein 2021 Table 1: K_Osm = 500 mOsm/kg〔事実〕。 | in-line 浸透圧計は別途調査〔未確定〕。 |
| `ammonia` | **< 4–6 mM（設計仮説）** | at-line Nova FLEX2 | `set_perfusion_rate` / `exchange_media` | `ammonia_high` | 哺乳動物培養で毒性閾値 4–6 mM（一般知見）〔推定〕。iPSC ネイティブ値は未特定〔未確定〕。 | A 層 v1 では **監視/記録のみ**、自動トリガは後段〔設計境界〕。 |

### 2.3 凝集体・密度 CPP（L1 監督制御、継代トリガ）

| 変数名 | 目標/範囲 | channel | actuator / tool | イベント | 根拠 | 不確実性 |
|---|---|---|---|---|---|---|
| `aggregate_diameter_um` | **150–350 µm**（範囲） | at-line 画像 / FBRM CLD / Ovizio DHM | `set_agitation_rpm` / `trigger_passage` | `aggregate_out_of_range` | Borys 2021: day5 で 169–275 µm、>400 µm で壊死予想。Manstein K_Agg=175 µm（径）もこの範囲内〔事実〕。 | in-line 連続計測は未実証、v1 は at-line 寄り〔推定〕。 |
| `vcd` | **~35×10⁶ cells/mL**（目標） | in-line capacitance（Aber/Hamilton/Sartorius） | `trigger_passage` | `vcd_target_reached` | Manstein 2021: 7 日で 35×10⁶ cells/mL〔事実〕。 | capacitance-VCD の iPSC 高密度線形性は未定量〔推定〕。 |
| `viability` | **> 90 %**（目標） | at-line Nova FLEX2 / 画像 | — | `viability_low` | 品質目標として一般的〔推定〕。 | L1 制御の直接対象ではなく BO 目的関数側〔設計境界〕。 |

### 2.4 灌流率（主アクチュエータ、条件起動）

| 変数名 | 目標/範囲 | channel | actuator / tool | イベント | 根拠 | 不確実性 |
|---|---|---|---|---|---|---|
| `perfusion_rate_vvd` | **0 → 7 vvd**（範囲） | actuator 状態 / 流量計 | `set_perfusion_rate` | `perfusion_ramp_trigger`（glucose/lactate/osmolality） | Manstein 2021 Table 3: 0→7 vvd over days 1-7〔事実〕。 | 0.5 vvd/step 等の ramp 値は設計仮説〔推定〕。 |

### 2.5 継代パラメタ

| 変数名 | 目標/範囲 | channel | actuator / tool | イベント | 根拠 | 不確実性 |
|---|---|---|---|---|---|---|
| `passage_method` | `dissociate`（v1 既定） | — | `trigger_passage` | `passage_requested` | kg_to_auto_cell.md §8#6 決定〔事実/設計選択〕。 | `dilute`/`split` は将来拡張〔未確定〕。 |
| `rock_inhibitor` | **Y-27632 添加** | — | `trigger_passage` | — | iPSC 解離後生存向上の標準プロトコル（ROCK 阻害剤）〔事実〕。 | 濃度/添加時間は細胞株依存〔未確定〕。 |
| `dissociation_intensity` | **上限あり** | — | `trigger_passage` | `shear_risk` | passage ノード: シアストレス管理が品質を左右〔事実〕。 | 具体的強度単位は装置/細胞株依存〔未確定〕。 |
| `target_seeding_density` | 細胞株/プロトコル依存 | — | `trigger_passage` | — | Manstein 2021 で 7 日 70 倍拡大〔事実〕。 | 数値は実験計画で決定、L1 は目標値を参照〔推定〕。 |

---

## 3. 各 CPP の「設定点 vs 制限値 vs 目標値」整理

| CPP | 設定点 | 下限制限 | 上限制限 | 目標値 | 備考 |
|---|---|---|---|---|---|
| pH | 7.1 | 7.0 | 7.3 | — | L0 PID、L1 は固定が基本。 |
| DO | 40% → 10% | 5% | 50% | — | 高密度では自然低下を許容。 |
| temp | 37 ℃ | 36.5 ℃ | 37.5 ℃ | — | L0 PID。 |
| agitation | — | 50 rpm | 120 rpm | 40–60 rpm | Borys 最適域で運転、120 rpm は非常時上限。 |
| glucose | — | 1.5 mM | — | > 2 mM | 1.5 mM = K_Glc（制限/トリガ）。 |
| lactate | — | — | 50 mM | < 30 mM | 50 mM = K_Lac（制限）。 |
| glutamine | — | 0.01 mM | — | > 0.1 mM | 0.01 mM = K_Gln（制限/トリガ）。 |
| osmolality | — | — | 500 mOsm/kg | < 400 mOsm/kg | 500 = K_Osm（制限）。 |
| ammonia | — | — | 4–6 mM（仮） | < 2 mM | v1 監視/記録のみ。 |
| aggregate diameter | — | 150 µm | 350 µm | 200–300 µm | >400 µm で壊死リスク。 |
| VCD | — | — | — | 35×10⁶/mL | 継代トリガ。 |
| perfusion rate | 0→7 vvd（スケジュール） | 0 vvd | 7 vvd | glucose/lac/osm 最適化 | 条件起動で ramp。 |

---

## 4. 変化率制限（ramp 制限）

### 4.1 根拠

急激な灌流率変更は浸透圧ショック、シアストレス、培地コスト変動を引き起こす。撹拌/DO 設定点の急変は凝集体破砕または酸化ストレスを引き起こす。

### 4.2 Ramp 制限表

| アクション | 最大変化率 | 根拠 | 実装上の位置 |
|---|---|---|---|
| `set_perfusion_rate` | **±0.5 vvd / 30 min** | Manstein 2021 Table 3 の 0→7 vvd / 7 日から 1 vvd/日を超えない設計仮説〔推定〕。 | `validate_tool_call` 変化率チェック。 |
| `set_agitation_rpm` | **±20 rpm / 5 min** | 凝集体破砕/シア回避（Borys 2021 の 40 rpm 最適域から急変回避）〔推定〕。 | `validate_tool_call`。 |
| `set_gas_setpoint(DO)` | **±5 % / 5 min** | 酸化還元ストレス回避〔推定〕。 | L0 PID カスケード内包絡線。 |
| `set_gas_setpoint(pH/CO₂)` | **±0.1 / 5 min** | pH ショック回避〔推定〕。 | L0 PID カスケード内包絡線。 |
| `trigger_passage` | 離散イベント | シア上限 + Y-27632 同時添加を強制〔設計選択〕。 | `validate_tool_call` + LADS Program。 |

> これらの数値は **R&D 一次での初期仮説**であり、実機/細胞株でチューニングが必要〔未確定→推定〕。GMP 移行時は検証済包絡線に昇華する。

---

## 5. 欠落 CPP の検討

| 候補 | A 層 v1 で必要か | 判断理由 |
|---|---|---|
| ammonia | **監視のみ** | 毒性は知られるが、iPSC ネイティブ閾値・in-line 計測が未確定。トリガは後段。 |
| glutamate | 後段 | グルタミン代謝副産物。Nova FLEX2 で測定可だが、制限値未確定。 |
| 培地交換率 | 内包 | 灌流率 vvd に統合。ボーラス交換は `exchange_media` イベント。 |
| 液量 / 槽レベル | 監視推奨 | 灌流の質量バランス計算に必要。LADS level sensor Function で取得〔推定〕。 |
| 泡（foam） | 監視のみ | 培地撹拌プロセスの汎用的脅威。自動消泡剤添加は v1 非対象。 |
| 圧力 | 監視のみ | 閉鎖系の無菌バリア監視。LADS pressure Function。 |
| ガス流量 | 監視のみ | DO/pH 制御の二次指標。 |
| 品質マーカー（OCT4 等） | **BO 目的関数専用** | offline/run 単位。L1 制御対象外〔設計境界〕。 |
| 無菌/汚染 | **イベント専用** | online 検知手段未確定、`contamination_suspected` は即時エスカレーション。 |

---

## 6. 未確定・要追加調査の CPP リスト

| # | 項目 | 理由 | 次のアクション |
|---|---|---|---|
| 1 | ammonia 閾値（iPSC ネイティブ） | 一般哺乳動物値の転用で不確実 | 文献サーチ or 実験決定 |
| 2 | in-line 浸透圧計 | 計測器選定未確定 | P5 継続 / ベンダ確認 |
| 3 | capacitance-VCD 線形性 @ 35×10⁶/mL | Manstein で定性一致、定量 R² なし | 校正実験 |
| 4 | 凝集体径 in-line 連続計測 | turnkey iPSC 実証が薄い | at-line 画像 v1、in-line は後段 |
| 5 | Y-27632 濃度/添加時間 | 細胞株依存 | プロトコル固定 or BO 対象 |
| 6 | 解離強度の単位/上限 | 装置/細胞株依存 | 実機協業で ICD 化 |
| 7 | ramp 数値の実証 | 初期仮説 | Tier2 plant + 実 run で同定 |

---

## 7. L0-L3 分離と CPP の対応

| 層 | 関与する CPP | 備考 |
|---|---|---|
| **L0 局所 PID** | pH, DO, temp | 秒オーダー、検証済、ブレイン停止時も継続。 |
| **L1 決定的レシピ/ルール** | glucose, lactate, glutamine, osmolality, agitation, perfusion_rate, aggregate_diameter, VCD | 30 s+ 周期、条件起動、包絡線内自律。 |
| **L2 BO** | 全 CPP の設定点/範囲、run 間最適化 | qccrit（品質）を目的関数に含む。 |
| **L3 LLM** | 例外/曖昧知覚/承認仲介 | 包絡線外 setpoint 変更、継代承認。 |

---

## 8. Human-on-the-loop 承認フローとの関係

| アクション | 承認要否 | 理由 |
|---|---|---|
| 包絡線内 `set_perfusion_rate` | 不要 | L1 自律。 |
| 包絡線外 setpoint 変更 | **要承認** | L3 仲介、理由ログ必須。 |
| `trigger_passage` | **要承認** | 重大アクション、品質リスク。 |
| BO 提案採用 | **要承認** | 包絡線を外れる可能性あり。 |
| 緊急停止/ホールド | 安全系が強制、ブレインは要求のみ | L0/L1 フェイルセーフ。 |

---

## 9. トレーサビリティ

| 設計要素 | 参照 KG ノード | 一次出典 |
|---|---|---|
| 浮遊速度論/6 定数 | `kinetics`, `src_manstein` | Manstein 2021 (DOI 10.1002/sctm.20-0453, PMID 33660952, PMC8666714) |
| 撹拌/凝集体 CPP | `src_borys` | Borys 2021 (PMC7805206) |
| 灌流 0→7 vvd | `src_manstein` | Manstein 2021 Table 3 |
| 到達密度差 | `src_traj` | Nogueira 2019 (PMC6744632), Olmer 2012 (PMC3460618) |
| 制御権限分界 | `ctrl_split`, `loop` | kg_to_auto_cell.md §7.2 |
| 観測性スタック | `cpv`, `envmon` | P5 調査レポート |
| 規制制約 | `alcoa`, `csv`, `audit` | 各種規制ガイダンス（R&D 一次で ALCOA-lite） |

---

## 10. 設計境界

- **樹立（reprog）、分化（diff）、双腕ロボ（dualarm）、接着 2D 培養（conf）**: A 層制御対象外。`qccrit` 等は BO 目的関数の「正解ラベル」として参照するが、L1 runtime 制御には直接入れない。
- **GMP フル準拠（Part11/電子署名/完全 CSV）**: R&D 一次で soft 目標。技術的統制は ALCOA-lite として実装するが、最終適合はプログラム全体の責務。
- **RL**: 研究段階。A 層 v1 では採用しない。

---

## 11. 事実/推定/未確定ラベル集計

| ラベル | 数（概算） |
|---|---|
| 事実 | ~45（Manstein/Borys 原典、KG 確定事項） |
| 推定 | ~20（ramp 数値、校正精度、装置依存値） |
| 未確定 | 7（§6 リスト） |

