# A 層観測性スタック設計根拠レポート（agent_observability_stack）

## 1. 要約

auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター、Manstein 型灌流 0→7 vvd、目標密度 ~35×10⁶ cells/mL）の観測性スタックは、**物理 CPP（pH/DO/温度/撹拌/VCD/代謝物/浸透圧/凝集体径）を in-line / at-line で継続計測**し、L1 決定的監督制御の入力とすることを根拠付ける。品質（未分化マーカー等）と無菌性については、現時点で低遅延・検証済みの online 手段が確認できないため、**offline/run 単位の BO 目的関数専用**とする（設計境界）。v1 では VCD に in-line capacitance、代謝物には in-line Raman（または at-line Nova FLEX2）、凝集体径には at-line 画像/FlowCam を推奨する。

## 2. 前提とスコープ

- 対象プロセス: iPSC 浮遊/凝集体培養、Manstein 型灌流（0→7 vvd）、目標密度 ~35×10⁶ cells/mL。〔事実：Manstein 2021, PMID 33660952〕
- 運転形態: R&D / プロセス開発（一次）、Human-on-the-loop。〔事実：requirements.md §0〕
- 制御アーキ: ADR-0001（L0 局所 PID + L1 決定的レシピ/ルール + L2 ベイズ最適化 + L3 薄い LLM オーケストレータ）。〔事実：adr/0001-control-architecture.md〕
- 適用段階: **A 層に限定**。樹立/分化/双腕/接着 conf は**設計境界**として参照しない。〔事実：kg_to_auto_cell.md §1〕

## 3. 入力資料

| 資料 | 用途 |
|---|---|
| `docs/design/requirements.md` | R&D/Human-on-the-loop 前提、FR/NFR |
| `docs/design/kg_to_auto_cell.md` §4.2 | CPP と観測性の対応（P5 反映済） |
| `docs/design/adr/0001-control-architecture.md` | L0-L3 分離、BO/offline 品質の位置づけ |
| `docs/knowledge_graph/research/2026-06-15_P5_observability.md` | 計測器サーベイ・出典 |
| `docs/knowledge_graph/research/2026-06-14_P1_kinetics_cpp.md` | CPP 数値の文献根拠 |
| `docs/knowledge_graph/knowledge_graph.json` / `nodes.csv` / `edges.csv` | KG ノード ID 整合 |

## 4. A 層 CPP 観測性マトリクス

| CPP | 目標/範囲 | 計測原理/機器 | 配置 | cadence | 用途 | 確度ラベル | 主な出典 |
|---|---|---|---|---|---|---|---|
| pH | 7.1 | ガラス/ISFET プローブ | in-line | 連続 | L0 PID 制御、L1 監視 | 〔事実〕 | Manstein 2021; kg_to_auto_cell §4 |
| DO | 40 %→10 % | 光学/極譜式プローブ | in-line | 連続 | L0 PID 制御、L1 監視 | 〔事実〕 | Manstein 2021; kg_to_auto_cell §4 |
| 温度 | 37 ℃ | RTD/サーミスタ | in-line | 連続 | L0 PID 制御 | 〔事実〕 | kg_to_auto_cell §4 |
| 撹拌 | 50–120 rpm | エンコーダ/setpoint フィードバック | in-line | 連続 | L0 局所/L1 監督 setpoint | 〔事実/推定〕 | Borys 2021; kg_to_auto_cell §4 |
| VCD | ~35×10⁶ cells/mL | **capacitance/誘電分光**（Aber/Hamilton/Sartorius） | in-line | ~30 s | L1 灌流/継代トリガ、L2 BO | 〔推定〕 iPSC 高密度線形性は校正前提 | P5; Krause 2023; Manstein 2021 |
| グルコース | >1.5 mM | in-line Raman / at-line Nova FLEX2 | in-line/at-line | ~1 min / ~4.5 min | L1 feed/灌流トリガ | 〔推定〕 iPSC 再校正必須 | P5; Graf 2022; Nova FLEX2 |
| 乳酸 | <50 mM | in-line Raman / at-line Nova FLEX2 | in-line/at-line | ~1 min / ~4.5 min | L1 灌流トリガ | 〔推定〕 | P5; Graf 2022; Nova FLEX2 |
| グルタミン | >0.01 mM | in-line Raman / at-line Nova FLEX2 | in-line/at-line | ~1 min / ~4.5 min | L1 feed トリガ | 〔推定〕 | P5; Manstein 2021; Nova FLEX2 |
| アンモニウム | 監視値 | at-line Nova FLEX2 | at-line | ~4.5 min | L1 監視（毒性早期発見） | 〔推定〕 | Nova FLEX2 |
| 浸透圧 | <500 mOsm/kg | at-line Nova FLEX2（凝固点降下） | at-line | ~4.5 min | L1 灌流トリガ | 〔事実/推定〕 | Manstein 2021; Nova FLEX2 |
| 凝集体径 | 150–350 µm | at-line 画像（FlowCam/バイパス顕微鏡）/ FBRM / Ovizio | at-line/in-line | 離散/連続 | L1 撹拌/継代トリガ | 〔推定〕 v1 は at-line 寄り | P5; Borys 2021; Kropp 2019 |
| 灌流率 | 0→7 vvd | 流量計/setpoint フィードバック | in-line | 連続 | L1 主レバー | 〔事実〕 | Manstein 2021; kg_to_auto_cell §7.2 |
| 生存率 | 監視値 | Nova FLEX2 / 画像 | at-line/offline | ~4.5 min/run 単位 | L2 BO 入力 | 〔推定〕 | Nova FLEX2 |
| 品質マーカー | 受入基準 | フローサイト/qPCR/IF/核型 | offline | run 単位 | L2 BO 目的関数 | 〔未確定〕 online 代替不在 | P5 |
| 無菌性 | 逸脱ゼロ | rapid micro / offline 検査 | offline/rapid | run 単位 | CAPA トリガ | 〔未確定〕 online 手段未確認 | P5 |

## 5. 計測器の比較と選定根拠

### 5.1 VCD/biomass — capacitance センサ

| 項目 | Aber FUTURA | Hamilton Incyte Arc | Sartorius BioPAT ViaMass |
|---|---|---|---|
| 原理 | 誘電分光（RFI）、580 kHz 線形モデル | 誘電率（permittivity）、複数周波数対応 | インピーダンス分光、Aber 技術ベース |
| レンジ | 細胞培養汎用（cells/mL 換算） | 5×10⁵ – 8×10⁹ cells/mL（哺乳類） | 細胞培養汎用 |
| 出力 | Modbus / 4-20 mA 等 | RS485 Modbus | BioPAT MFCS/DCU 統合 |
| iPSC 実証 | Manstein 500mL 灌流で offline VCD と定性的一致（R² 未定量）〔推定〕 | iPSC 汎用実証は校正前提〔推定〕 | iPSC 汎用実証は校正前提〔推定〕 |
| 校正 | 細胞株/培地/サイズ分布別に offline VCD 校正必須 | 同左 | 同左 |
| 推奨用途 | 研究用撹拌槽（開 IF） | 研究用撹拌槽（PG13.5） | Sartorius バイオリアクター統合 |
| 出典 | Aber app note | Hamilton specs | Sartorius ViaMass page |

**設計判断**: VCD は in-line capacitance を anchor とする（Manstein でも使用）。〔推定〕 iPSC 高密度（~35×10⁶/mL）での線形性は、細胞径・生存率補正込みの校正モデルが必要。Aber/Hamilton/Sartorius はいずれも原理的に 35×10⁶/mL 以上までカバー可能だが、iPSC 特異的補正式は未確定。〔未確定：capacitance-VCD 線形性の iPSC 定量データ〕

### 5.2 代謝物 — in-line Raman vs at-line Nova FLEX2

- **in-line Raman**: CHO 灌流で PID 閉ループ glucose 制御が実証されており、glucose/lactate/gln/glu を同時推定可能。〔事実：Graf/Wei 2022, DOI 10.3389/fbioe.2022.719614〕ただし chemometric モデルは iPSC 培地・細胞密度で再構築必須。〔推定〕
- **Nova BioProfile FLEX2**: 16 項目（Gluc/Lac/Gln/Glu/NH4+/Na+/K+/Ca++/pH/PCO2/PO2/総細胞/VCD/生存率/細胞径/浸透圧）を 275 µL・4.5 分で計測。〔事実：Nova FLEX2 specs〕OPC 接続/OLS（Online Autosampler）により 10 槽まで自動サンプリング可能。〔事実：Nova FLEX2 specs〕

**設計判断**: v1 は Nova FLEX2（OLS）を at-line リッチパネルとして必須、Raman は閉ループ応答速度が必要な場合の追加オプションとする。これにより、BO 入力・Raman 校正の「正解ラベル」も同じ Nova データで得られる。〔提案〕

### 5.3 凝集体径 — Ovizio / FBRM / at-line 画像

| 方式 | 原理 | 配置 | 長所 | 短所/留保 | 出典 |
|---|---|---|---|---|---|
| Ovizio iLINE-F PRO | D3HM デジタルホログラフィ顕微鏡 | in-line（バイパス循環） | ラベルフリー、連続、細胞/凝集体を 3D 計測 | iPSC 凝集体実証は薄い、高価 | Ovizio/Merck リリース; Ovizio datasheet |
| FBRM ParticleTrack G400 | Focused Beam Reflectance（弦長分布 CLD） | in-situ | 連続、濃厚懸濁可 | **CLD ≠ 真の径 PSD**、形状依存、凝集体に対して解釈困難 | MT ParticleTrack page |
| at-line 画像（FlowCam/Kropp 型バイパス） | フローイメージング顕微鏡 | at-line/bypass | 真の画像・形態、iPSC 実証あり（50→260 µm） | 離散/日次、サンプリング遅延 | Kropp 2019; FlowCam specs |

**設計判断**: v1 では **at-line 画像（FlowCam または Kropp 型バイパス顕微鏡）を推奨**。凝集体径は L1 での制御に使うが、in-line 連続計測が必須ではない（Borys 2021 からも撹拌→径の応答は比較的遅い）。Ovizio/FBRM は将来段階の検討対象。〔提案〕

## 6. v1 推奨観測性スタック

### 6.1 必須（L0/L1 閉ループの minimum viable stack）

| 層 | 計測 | 用途 |
|---|---|---|
| L0 | pH/DO/温度プローブ（標準） | 局所 PID |
| L0/L1 | 撹拌 rpm フィードバック | 局所制御 + 凝集体制御 setpoint |
| L1 | **in-line capacitance VCD** | 灌流率/継代トリガの anchor |
| L1 | **at-line Nova FLEX2（OLS）** | 代謝物/浸透圧/生存率/細胞径の正解ラベル、BO 入力 |
| L1 | **at-line 凝集体画像** | 凝集体径トレンド、継代/撹拌判断 |

### 6.2 追加オプション（優先度順）

1. **in-line Raman**: glucose/lactate 閉ループを高速化する場合。ただし Nova データによる校正・モデル管理が前提。
2. **Ovizio iLINE-F PRO**: 凝集体径を連続化したい場合（予算・実証許容なら）。
3. **FBRM G400**: CLD トレンドの監視用。径の絶対値としては補正が必要。

### 6.3 BO/offline 専用（L2）

- 未分化/多能性マーカー（OCT4/SOX2/NANOG/SSEA/TRA）：フローサイト/qPCR/IF
- 核型/同一性/自発分化：offline
- 無菌/汚染：rapid micro / 培養終了後検査

これらは run 単位の BO 目的関数を構成し、run 内の L1 制御には直接フィードバックしない。〔推定：低遅延 online 手段の不在〕

## 7. 校正・メンテナンス要件

| 計測 | 校正 | メンテナンス | ALCOA/監査上の記録 |
|---|---|---|---|
| pH/DO | 2 点校正（pH 7/10、DO 0/100%） | プローブ交換/滅菌サイクル | 校正日時、標液ロット、実施者 |
| 温度 | 1 点基準温度校正 | 定期的な精度確認 | 同上 |
| capacitance VCD | 細胞株毎に offline VCD/viability/細胞径との回帰式（線形または Cole-Cole/PLS） | プローブ清掃、周波数応答確認 | 校正モデル ID、使用データ範囲、R²/RMSEP |
| Raman | chemometric モデル構築・再検証（Nova データを正解） | プローブ清掃、モデル性能モニタリング | モデルバージョン、校正セット、予測精度 |
| Nova FLEX2 | MicroSensor Card 自動校正、QC 流体確認 | カートリッジ交換（~21 日）、廃液処理 | カードロット、有効期限、使用量 |
| 凝集体画像 | スケールバー/ピクセルサイズ、分類器再学習 | フォーカス/照明確認 | 画像保存、分類器バージョン、再学習日 |

## 8. 未解決項目

1. **#11 品質読み出し**: run 毎に測定可能な品質指標の具体構成と、label-free 画像による代理指標の有効性は未確定。現状 offline 専用とする。〔未確定〕
2. **#17 無菌検知**: 閉鎖系 iPSC 灌流培養で、低遅延かつ検証済みの online/rapid 無菌検知手段が確認できていない。〔未確定〕
3. **capacitance-VCD 高密度線形性**: Manstein 2021 は定性的一致のみ報告。~35×10⁶/mL でのサイズ分布補正込み R²/RMSEP の定量的実証が必要。〔未確定〕
4. **Raman chemometric モデル**: iPSC 培地/凝集体状態下での glucose/lactate 予測精度は未実証。〔未確定〕

## 9. L0-L3 分離との対応

- **L0（局所 PID）**: pH/DO/温度/撹拌の連続計測と高速制御。auto_cell は setpoint のみ書き換え、PID ループはデバイス局所。〔事実：adr/0001 §Decision〕
- **L1（決定的監督制御）**: VCD、代謝物、浸透圧、凝集体径をイベント駆動で監視。`set_perfusion_rate`/`set_agitation_rpm`/`trigger_passage` 等を包絡線内で自律実行。〔事実：kg_to_auto_cell §7.2〕
- **L2（BO）**: run 間の設定点/レシピ最適化。入力は Nova/画像/offline 品質データ。多忠実度では Tier2 `plant_model` を低忠実評価に使用。〔事実：adr/0001 §BO〕
- **L3（LLM オーケストレータ）**: センサ異常・画像判断の曖昧さ・包絡線外 BO 提案の承認仲介。毎周期ではなくイベント駆動。〔事実：adr/0001 §Decision〕

## 10. 設計境界

- 樹立/分化/双腕/接着 conf における観測性（コンフルエンシー、分化マーカー画像等）は A 層スコープ外。〔事実：requirements.md §5〕
- GMP 完全準拠 CSV/Part11 実装は R&D 一次として緩いが、将来排除しない形で ALCOA-lite ログを設計。〔事実：requirements.md §5〕

## 11. 出典

| ID | タイトル | URL / DOI / PMID / PMCID |
|---|---|---|
| src_manstein_sctm | Manstein et al. 2021, Stem Cells Transl Med | DOI 10.1002/sctm.20-0453, PMID 33660952 |
| src_manstein_star | Manstein et al. 2021, STAR Protocols | DOI 10.1016/j.xpro.2021.100988, PMID 34917976, PMC8666714 |
| src_borys | Borys et al. 2021, Stem Cell Res Ther 12:55 | PMC7805206 |
| src_kropp2019 | Kropp et al. 2019, Sci Rep — at-line bypass imaging | https://www.nature.com/articles/s41598-019-48814-w |
| src_krause2023 | Krause et al. 2023, Curr Opin Biotechnol | DOI 10.1016/j.copbio.2023.102979 |
| src_graf2022 | Graf/Wei et al. 2022, Front Bioeng — in-line Raman PID glucose | DOI 10.3389/fbioe.2022.719614 |
| src_aber | Aber FUTURA — optimized perfusion by capacitance | https://aberinstruments.com/application/optimized-perfusion-by-capacitance-process-measurement-control/ |
| src_hamilton | Hamilton Incyte Arc specs | https://www.hamiltoncompany.com/sensors/cell-density-sensors/incyte |
| src_sartorius | Sartorius BioPAT ViaMass | https://shop.sartorius.com.cn/us/p/biopatviamass/BioPAT_Viamass |
| src_nova | Nova BioProfile FLEX2 | https://www.novabiomedical.com/cell-culture-analyzers/bioprofile-flex2/ |
| src_ovizio | Ovizio iLINE-F PRO / Merck partnership | https://www.bioprocessonline.com/doc/ovizio-imaging-systems-is-entering-into-a-commercial-partnership-with-merck-to-promote-its-iline-f-pro-solution-for-the-cell-gene-therapy-market-0001 |
| src_fbrm | Mettler Toledo ParticleTrack with FBRM | https://www.mt.com/my/en/home/products/L1_AutochemProducts/particle-size-analyzers/particletrack-fbrm.html |
| src_flowcam | FlowCam — What is FlowCam? | https://www.fluidimaging.com/blog/what-is-the-flowcam |
| src_p5 | P5 observability research memo | `docs/knowledge_graph/research/2026-06-15_P5_observability.md` |
| src_kg_bridge | KG → auto_cell 設計ブリッジ §4.2 | `docs/design/kg_to_auto_cell.md` |

---

*生成日: 2026-06-16 / agent_observability_stack（Mode A）*
