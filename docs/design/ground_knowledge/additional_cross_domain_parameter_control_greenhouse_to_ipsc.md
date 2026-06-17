# 追加調査: auto_JA（温室/水耕）のパラメータ制御知見を auto_cell（iPSC 培養）へ適用

> **担当**: cross-domain controls Agent（auto_JA → auto_cell）  
> **Scope**: auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御、Manstein 型灌流 0→7 vvd）  
> **Date**: 2026-06-17  
> **前提**: ADR-0001（L0 局所 PID + L1 決定的レシピ/ルール + L2 BO + L3 薄い LLM）、R&D 一次・Human-on-the-loop  
> **対象知見元**: `/home/sin/code/agent/auto/auto_JA/docs/research/`（温室環境制御・水耕・harsh IoT・BO/EIG 関連調査）

---

## 1. Executive Summary

本調査は、隣接プロジェクト auto_JA で蓄積された **温室/水耕環境におけるパラメータ制御・最適化・センサ運用の知見**を、auto_cell の iPSC 浮遊灌流培養文脈で再解釈し、適用可能性を評価するものである。結論から述べると、**制御アーキテクチャの上位設計（L0/L1/L2/L3 分離、イベント駆動、2 層センサ校正、BO/EIG 探索、安全制約）には相当部分が流用可能だが、培養対象が「作物」から「生細胞・凝集体」に変わることで、無菌・品質・継代・GMP-ready という独自の制約が加わる**。

主要結論:

1. **制御層分離（L0 局所 PID / L1 決定的レシピ / L2 BO / L3 薄い LLM）の設計パターンは流用可能**〔設計判断〕。auto_JA の水耕液系制御（pH/DO/温度/流量）と auto_cell の iPSC 培養は、センサ・アクチュエータの低層が類似している。
2. **run 間パラメータ最適化において、BO・多目的 BO・安全制約付き BO・バッチ並列 BO・EIG 獲得戦略は直接転用可能**〔推定〕。ただし、auto_cell の試行単位は「作期」ではなく「1 バッチ/run」であり、試行コスト・時間スケール・目的関数が異なる。
3. **多忠実度評価・転移 BO・事前知識による GP 事前分布初期化は、iPSC 培養のデータ効率化に有効**〔推定〕。シミュレータ（Manstein ODE/Tier2 plant_model）を低忠実度評価、実 run を高忠実度評価とする構成が自然に対応する。
4. **2 層センサネットワーク（高精度基準ノード＋廉価高密度ノード）と転移校正のアイデアは、培養槽群や複数装置間のセンサドリフト補正に応用可能**〔推定〕。ただし、iPSC 培養の「無菌バリア」と「in-line 校正の困難さ」は障害となる。
5. **イベント駆動型 ReAct ループ（生センサ毎ではなく検出イベントで起動）は、auto_cell の L1/L3 設計と整合する**〔事実〕。ただし、細胞培養では異常検出の偽陽性が高コストなので、信頼度スコア層との組み合わせが必須。
6. **GreenLight-Gym/PCSE/WOFOST/APSIM 等の作物シミュレータは iPSC 培養には直接使えない**〔事実〕。制御知見（EIG 活用、シミュレータ・実機ギャップ管理）のみを流用する。
7. **作物保護のための Safe BO は、iPSC 培養では「細胞品質・未分化性維持・無菌保全」への制約 BO に読み替える**〔設計判断〕。

---

## 2. 背景：auto_JA 側のパラメータ制御知見

### 2.1 制御対象と階層

auto_JA（温室/水耕）では、以下を対象とする。

| 層 | 対象 | 周期 | 主要アプローチ |
|---|---|---|---|
| 環境制御 | 温度/湿度/CO₂/換気/照明 | 秒〜分 | PID / on-off / 設定制御 |
| 灌水・施肥 | pH/EC/灌水量/液温/DO | 分〜時間 | ルールベース / BO / ルーチン制御 |
| run（作期）間最適化 | 昼夜温度・EC・pH・灌水・受光・CO₂・整枝スケジュール | 作期単位（数週〜数月） | ベイズ最適化（BO）・EIG・多目的 BO |
| オーケストレーション | 複数棟/ゾーンの並行運転、人への承認仲介 | イベント駆動 | LLM（ReAct）/ ツール呼び出し |

出典: `proposal.md` §4.5, `simulator_introduction_plan.md` §2.1, `SPReAD_第2回_応募素案.md` §5

### 2.2 最適化・探索手法

| 手法 | 用途 | auto_JA での位置づけ |
|---|---|---|
| ガウス過程（GP）+ EI/NEI | 次の試行点選択 | 標準 BO フロー |
| `qNEHVI` | 収量/コスト/品質/労務の多目的最適化 | 将来拡張 |
| Safe BO | 実圃場での作物保護 | 将来拡張 |
| バッチ並列 BO（`q-EI`/`qNEHVI`） | N 区画で 1 作期あたり N 評価 | 将来拡張 |
| EIG / `GIBBON` / `MES` | 情報利得最大化、試行予算削減 | 理論・ソフトウェア開発段階 |
| 多忠実度 | シミュレータ・生育初期指標を安価評価とする | 将来拡張 |
| 転移 BO / メタ BO | 前作/他地域/言語注釈から事前分布初期化 | 将来拡張 |
| 強化学習（RL） | GreenLight-Gym での制御軌道学習 | 採用しない（データ量不足） |

出典: `proposal.md` §4.5, `simulator_introduction_plan.md` §4.3–§4.4, `survey_academic_approaches.md` §4.3–§4.4

### 2.3 センサ・観測運用

| 知見 | 内容 |
|---|---|
| 2 層センサネットワーク | 高精度基準マスト（SHT41/SCD30/AS7341）＋廉価高密度ノード（AHT25/SCD40/ESP32） |
| 転移校正 | 基準ノードを教師としたドリフト補正 |
| 観測密度 | 空気質（全マスト）、分光 PAR（代表 3 マスト）、R:FR（1 マスト）、入射基準（1 点共有） |
| 光測定の物理的罠 | 群落内では平板型 Si フォトダイオードが PAR を 20–40% 過大評価 → opal 拡散球等が望ましい |
| 通信 | BLE（近接）/ LoRa 920MHz（遠隔）/ LTE ゲートウェイの 3 層 |
| 電源 | 商用 12V 配電主体＋オフグリッド検証機（LiFePO4＋ソーラー） |
| 異常検出 | PELT（変化点）/ BOCPD（オンライン）/ 深層異常検出 |

出典: `greenhouse-harsh-iot-survey.md`, `greenhouse-harsh-iot-bom-budget.md`, `survey_academic_approaches.md` §7.2

### 2.4 シミュレータと実機ギャップへの言及

| 知見 | 内容 |
|---|---|
| シミュレータの目的 | BO 収束特性・パラメータ感度の事前確認、EIG による試行予算削減の定量的検証 |
| 対象シミュレータ | PCSE/WOFOST（作物成長）、APSIM（土壌/水/栄養）、GreenLight-Gym（温室制御） |
| 日本適用時のギャップ | 品種パラメータ不足、気象データ 5 日遅れ、土壌パラメータ変換、収量→市場価格の別途連携 |
| ライセンス | EUPL-1.2/AGPL-3.0/商用ライセンス等、専用 venv/Docker で隔離 |
| 実装ギャップ | `ml/experiment_design` は `q-EI/qNEHVI` のみ、EIG 未実装；IoT 2 層ノード網も設計書のみ |

出典: `simulator_introduction_plan.md`, `SPReAD_第2回_応募素案_評価レポート.md` §3.1

---

## 3. auto_cell 側の文脈との対応マッピング

### 3.1 制御対象の類型比較

| 観点 | auto_JA（温室/水耕） | auto_cell（iPSC 浮遊灌流） |
|---|---|---|
| 制御対象 | 作物、土壌/培養液、ハウス環境 | 生細胞（凝集体）、培養液、バイオリアクター環境 |
| 制御周期 | 秒〜作期 | 秒（L0）、30 s+（L1）、run 単位（L2） |
| 主要レバー | 灌水/施肥/CO₂/加温/換気/照明 | 灌流率/撹拌/DO/pH 設定点/給餌/継代 |
| 安全要件 | 作物保護 | **無菌・細胞品質・未分化性・GMP-ready** |
| 試行単位 | 1 作期（数週〜数月） | 1 run/batch（数日〜1 週間） |
| 目的関数 | 収量/品質/コスト/労務 | VCD/生存率/多能性マーカー/培地コスト/乳酸抑制 |
| 外乱 | 気象/日射/病害/市場 | 細胞株変動/凝集動態/温度ラボジット/培地ロット |
| 追加固有要素 | 気象・市場・品種 | **継代・凝集体・無菌・規制** |

### 3.2 制御階層の対応

| auto_JA 層 | auto_cell 層 | 流用可否 |
|---|---|---|
| 環境 PID/on-off | L0 局所 PID（温度/pH/DO/撹拌） | ✅ 直接流用可能（制御対象が液系で類似） |
| 灌水・施肥ルーチン | L1 決定的レシピ/ルール | ✅ 概念流用（トリガー/ランプ制限/包絡線） |
| 作期間 BO | L2 run 間 BO | ✅ 手法流用（試行単位・目的関数の違いに注意） |
| LLM オーケストレーション | L3 薄い LLM | ✅ 設計パターン流用（ただし auto_cell はさらに薄い） |
| 2 層センサネットワーク | バイオリアクター群センサ校正 | ⚠️ 概念流用（無菌/in-line 制約あり） |
| 作物シミュレータ | Manstein ODE / Tier2 plant_model | ❌ モデルは流用不可、探索手法のみ流用 |

---

## 4. 適用可能性評価（テーマ別）

### 4.1 ベイズ最適化（BO）と EIG

| auto_JA 知見 | auto_cell への適用 | 評価 | 備考 |
|---|---|---|---|
| GP + `q-EI` の標準フロー | run 間パラメータ最適化 | ✅ 推奨 | auto_cell でも L2 BO の標準フローとして採用済み |
| `qNEHVI` 多目的 BO | 収量/品質/コストの多目的化 | ✅ 推奨 | 目的関数：VCD×生存率×多能性陽性率など |
| Safe BO | 品質制約付き BO | ✅ 推奨 | 制約：STR 同一性、核型/CNV、未分化マーカー、無菌 |
| バッチ並列 BO | 複数バイオリアクター並行試行 | ✅ 推奨 | 同じ細胞株ロットを N 槽で並行評価 |
| EIG / `GIBBON` / `MES` | 試行予算削減・パラメータ較正 | ⚠️ 有望 | EIG 実装は auto_JA でも未済。共同開発可能 |
| 多忠実度評価 | Tier2 plant_model + 実 run | ✅ 推奨 | Manstein ODE を低忠実度、実 run を高忠実度 |
| 転移 BO / メタ BO | 細胞株間/培地ロット間の転移 | ⚠️ 有望 | データが蓄積してから適用 |
| 言語注釈から GP 事前を初期化 | 文献知見・KG を BO 事前に注入 | ⚠️ 検討 | `survey_academic_approaches.md` §4.4 のアイデア |

**設計への影響**: auto_cell の L2 BO は、auto_JA と同じく BoTorch/Ax ベースで構築し、`q-EI` → `qNEHVI` → 制約 BO → EIG の段階的拡張路線を共有できる。

### 4.2 安全制約と信頼度スコア

| auto_JA 知見 | auto_cell への適用 | 評価 | 備考 |
|---|---|---|---|
| Safe BO（作物保護） | 品質制約付き BO | ✅ 読み替え可能 | 作物損失 → 細胞品質損失/バッチ廃棄 |
| 高確率で安全領域内に限定 | CPP 包絡線内で行動 | ✅ 整合 | ADR-0001 の L1 包絡線拘束と一致 |
| 異常検出器チューニング（PELT/BOCPD） | 培養プロセスの変化点検出 | ⚠️ 要検証 | 細胞培養のノイズ特性が異なる |

**設計への影響**: auto_cell では、BO GP 事後分散・Raman PLS Q 残差・画像 DL 不確実性から「信頼度スコア」を計算し、閾値未満で HITL エスカレーションする層を L2/L3 間に挿入する（`additional_mpc_for_ipsc.md` 等と整合）。

### 4.3 2 層センサネットワークと転移校正

| auto_JA 知見 | auto_cell への適用 | 評価 | 備考 |
|---|---|---|---|
| 高精度基準マスト＋廉価高密度ノード | 基準アナライザー＋in-line プローブ群 | ⚠️ 部分的 | 無菌バリア内では基準マストの追加設置が困難 |
| 転移校正 | 装置間/ロット間センサドリフト補正 | ⚠️ 有望 | Nova FLEX2 等 at-line 基準で校正 |
| 観測密度の最適化 | 全槽 pH/DO/温度 + 代表槽 Raman/画像 | ✅ 推奨 | コストと情報量のトレードオフ |
| 光測定の物理的罠 | Raman/OCT/画像の光散乱補正 | ⚠️ 類似 | 凝集体による光散乱は別の物理だが「センサの物理的理解が必要」という教訓は共通 |

**設計への影響**: iPSC 培養では in-line 校正が難しいため、**at-line 基準（Nova FLEX2、Raman 校正サンプル）＋ ロットごとの交換プローブ比較**を転移校正の現実的形態とする。

### 4.4 イベント駆動アーキテクチャ

| auto_JA 知見 | auto_cell への適用 | 評価 | 備考 |
|---|---|---|---|
| `detect_events` で起動 | L1/L3 のイベント駆動化 | ✅ 直接流用 | auto_cell でも `detect_events` ベース |
| 生センサ毎ではなく検出イベントで駆動 | センサフローを抑制 | ✅ 有効 | 高速 PID は L0 に任せる |
| 緩い heartbeat で徐変も拾う | 定期的な健康診断 | ✅ 有効 | 30 s〜数分単位の heartbeat |

**設計への影響**: auto_JA のイベント駆動パターンは auto_cell の ADR-0001 と整合している。ただし、細胞培養では「異常検出の偽陽性」が高コストなので、各イベントに信頼度スコアを付与し、承認ワークフローと連携する。

### 4.5 シミュレータ活用とギャップ管理

| auto_JA 知見 | auto_cell への適用 | 評価 | 備考 |
|---|---|---|---|
| シミュレータで BO 収束を事前確認 | Tier2 plant_model で L2 BO 収束確認 | ✅ 推奨 | Manstein ODE で初期検証 |
| EIG による試行予算削減 | 実 run 前の情報量評価 | ⚠️ 将来技術 | データが揃えば適用 |
| 品種パラメータ不足 → 現地再較正 | 細胞株・培地再較正 | ✅ 類似 | U1 未解決課題と一致 |
| 気象データ遅れ → manifest 記録 | 分析遅延 → manifest 記録 | ✅ 類似 | at-line/offline 分析のタイムスタンプ管理 |
| ライセンス隔離 | 専用 venv/Docker | ✅ 推奨 | auto_cell でもシミュレータは隔離 |

**設計への影響**: auto_cell では `sim/plant_model` を低忠実度シミュレータとして位置づけ、実 run データで GP バイアス補正を行う。auto_JA の「シミュレータ・実機ギャップ管理」プロセス（品種/土壌/気象の再較正）に倣い、細胞株/培地/温度ラボジットの再較正プロトコルを整備する。

### 4.6 外乱・遅延・通信/電源対策

| auto_JA 知見 | auto_cell への適用 | 評価 | 備考 |
|---|---|---|---|
| 安全 BO で不確実性高い領域を避ける | 高不確実性時は HITL エスカレーション | ✅ 整合 | 信頼度スコア層で実現 |
| 多忠実度で試行コスト抑制 | Tier2 plant_model → 縮小実験 → 実 run | ✅ 推奨 | Phase 2 以降 |
| 転移学習でデータ不足補う | 細胞株間転移 BO | ⚠️ 将来 | データ蓄積後 |
| センサ個体差・ドリフト → 転移校正 | プローブ交換/ロット差補正 | ⚠️ 部分的 | 無菌制約あり |
| 通信断 → microSD ロガー蓄積 | バイオリアクター SCADA のローカルバッファ | ✅ 類似 | 既存装置の機能を活用 |
| 電力不安定 → オフグリッド検証機 | ラボ停電対策（UPS/CO₂ バックアップ） | ⚠️ 既存設備 | 既存施設要件に依存 |

---

## 5. 流用可能な実装資産（physical-ai-core / auto_JA）

`kg_to_auto_cell.md` §3 および ADR-0001 で言及されている通り、auto_JA から以下の資産が流用可能である。

| 資産 | auto_cell への流用 | 備考 |
|---|---|---|
| MQTT-native トランスポート | `cell/{culture_unit_id}/cmd/...` 等の topic 契約 | `farm/`/`office/`/`hems/` に倣う新リネージ |
| WorldModel（センサ/画像取り込み） | 培養状態モデル・event_store | そのまま拡張 |
| DomainVertical ABC / plugin 機構 | `CellCulturePlugin(DomainVertical)` | 差分は継代・凝集体・無菌・規制 |
| tool_schemas / tool_handlers | 副作用ツール定義 | `set_perfusion_rate`, `trigger_passage` 等を追加 |
| sanitizer / validate_tool_call | 包絡線拘束・安全チェック | CPP 包絡線に置き換え |
| infra/virtual_edge | エッジセンサ結線検証 | 必要に応じて |

**分岐点**: auto_JA では毎周期 LLM 常駐が許容される可能性があるが、auto_cell では安全/再現性のため L3 はイベント駆動・非常駐とする。

---

## 6. 細胞培養文脈での追加調査・検証事項

以下は、auto_JA 知見を auto_cell に落とす際に追加で確認すべき事項である。

| # | 追加調査事項 | 理由 | 想定方法 |
|---|---|---|---|
| C1 | iPSC 培養での Safe BO 制約定義 | 作物保護から細胞品質保護への読み替え | 多能性マーカー・核型・STR を制約に追加 |
| C2 | BO 目的関数の細胞株依存性 | VCD/生存率/多能性の重みは株・製品によって異なる | 研究者ヒアリング + 少数 run で感度分析 |
| C3 | Tier2 plant_model の低忠実度評価精度 | Manstein ODE の細胞株再較正誤差を定量 | sim vs 実 run の比較 |
| C4 | Raman PLS の iPSC 校正 | CHO モデルは流用不可 | 実データで校正（`additional_raman_calibration_ipsc.md`） |
| C5 | 凝集体画像の自動セグメンテーション | 画像定量化は BO/MPC の入力に必要 | U-Net/Mask R-CNN 転移学習 |
| C6 | 複数バイオリアクター並行 BO の実装 | バッチ並列 BO を現実化 | BoTorch `qNoisyExpectedImprovement` |
| C7 | EIG 獲得関数の実装 | auto_JA でも未実装 | Pyro BOED / BoTorch 拡張 |
| C8 | センサドリフトの at-line 転移校正 | 無菌バリア内での校正方法 | Nova FLEX2 基準 + ロット比較 |
| C9 | 継代イベントの承認ワークフロー | 水耕には存在しない「状態リセット」 | HMI 設計（`agent_hmi_workflow.md`） |
| C10 | LLM 生成説明の誤帰属リスク対策 | auto_JA と同じリスク | 出典必須化・規則ベースフォールバック |

---

## 7. 推奨ロードマップ（cross-domain 知見の取り込み順）

| フェーズ | 期間 | auto_JA からの流用事項 | auto_cell 固有対応 |
|---|---|---|---|
| **v1 / Phase 1** | 0–6 ヶ月 | L0/L1/L2/L3 分離、イベント駆動、包絡線拘束、標準 BO フロー、MQTT topic 契約 | 無菌・継代・凝集体のルール追加、Manstein ODE 維持、Nova FLEX2 at-line、HITL |
| **Phase 2** | 6–18 ヶ月 | 多目的 BO、制約 BO、多忠実度評価、EIG プロトタイプ、2 層センサ校正概念 | Raman アドバイザリ、MPC シミュレーション、画像定量化、GP バイアス補正 |
| **Phase 3** | 18–36 ヶ月 | 転移 BO、メタ BO、高度な EIG、ハイブリッド DT | 多変数適応 MPC、Raman 閉ループ、GMP IQ/OQ/PQ 移行、Annex 22 AI/ML 検証 |

---

## 8. リスク・注意点

1. **CHO/温室由来の数値を iPSC に直接転用しない**〔設計判断〕。auto_JA の作物収量データや CHO mAb タイトル向上率は、iPSC の多能性維持・凝集体品質には当てはまらない。
2. **LLM を Critical 制御経路に置かない**〔設計判断〕。auto_JA でも生成説明の誤帰属リスクが指摘されている。auto_cell では L3 を薄く保ち、決定的 L0/L1/L2 が制御の主軸。
3. **無菌バリアはセンサ校正の自由度を制限する**〔事実〕。2 層センサネットワークの概念は有用だが、in-line 基準マストの設置は困難。at-line 基準を活用する。
4. **BO の試行コストは作物より高い場合がある**〔推定〕。1 run = 数日〜1 週間＋細胞・培地コスト。EIG/多忠実度/転移 BO はより強い動機となる。
5. **イベント駆動の異常検出は偽陽性に注意**〔推定〕。細胞培養では「停止/隔離」が高コスト。各イベントに信頼度スコアを付与する。

---

## 9. 結論・設計への影響

本調査により、auto_JA で蓄積された **パラメータ制御・BO/EIG・センサ運用・イベント駆動・シミュレータ活用**の知見は、auto_cell の iPSC 浮遊灌流培養制御において相当部分が流用可能であることが示された。特に、**L0/L1/L2/L3 の制御層分離、run 間 BO、2 層センサ校正の概念、イベント駆動アーキテクチャ**は、auto_cell の既存設計（ADR-0001）と整合し、実装資産も共有できる。

一方、**培養対象が「作物」から「生細胞・凝集体」に変わる**ことで、無菌・品質・未分化性・継代・GMP-ready という独自の制約が加わる。これらは単なる「読み替え」ではなく、制約定義・承認ワークフロー・センサ校正方法・目的関数設計に影響を与える。

**設計への影響**:

- v1（Phase 1）: auto_JA と同じく **L0 局所 PID + L1 決定的レシピ/ルール + L2 標準 BO + L3 薄い LLM** の骨格を維持。MQTT topic 契約・plugin 機構・sanitizer を流用する。
- Phase 2: **多目的 BO・制約 BO・多忠実度評価・EIG プロトタイプ**を auto_JA と共同で開発。Raman アドバイザリ・MPC シミュレーションと並行。
- Phase 3: **転移 BO・ハイブリッド DT・多変数適応 MPC**を検討。ただし Critical 制御経路は決定的 L0/L1 に留め、DT/BO/MPC はアドバイザリ/承認仲介に限定。

---

## 付録: 出典ファイル一覧

| ファイル | 主な関連トピック |
|---|---|
| `auto_JA/docs/research/proposal.md` | BO/EIG、多目的・安全・バッチ並列 BO、多忠実度、転移、イベント駆動 ReAct |
| `auto_JA/docs/research/simulator_introduction_plan.md` | シミュレータ評価、EIG（GIBBON/Pyro BOED）、BO ベースライン、ギャップ管理 |
| `auto_JA/docs/research/survey_academic_approaches.md` | BO 理論、異常検出、因果発見、GP 事前への知識注入 |
| `auto_JA/docs/research/greenhouse-harsh-iot-survey.md` | 2 層センサ、転移校正、I2C/電源/無線、光測定の物理 |
| `auto_JA/docs/research/greenhouse-harsh-iot-bom-budget.md` | 2 層 BOM、環境制御 PoC 予算 |
| `auto_JA/docs/research/implementation_gap_plan.md` | BO ハーネス骨格、安全制約、decision_outcomes |
| `auto_cell/docs/design/adr/0001-control-architecture.md` | L0/L1/L2/L3 分離、LLM は制御ループから外す |
| `auto_cell/docs/design/ground_knowledge/kg_to_auto_cell.md` | CPP カタログ、制御権限分界、auto_JA hydroponics との類型 |
| `auto_cell/docs/design/ground_knowledge/additional_mpc_for_ipsc.md` | MPC の将来位置づけ、状態/操作変数/制約定式化 |
| `auto_cell/docs/design/ground_knowledge/additional_pinn_dt_for_ipsc.md` | ハイブリッド DT、多忠実度 BO、データ要件 |
