# P5 調査レポート — iPSC 浮遊バイオリアクタの計測・観測性スタック

- 日付: 2026-06-15 ／ 手法: deep-research（5角度・26ソース・124主張→上位25を3票検証→20確定/5棄却）＋ 私による一次ソース検証（PMC8235132）
- 対象: auto_cell の ICD（LADS sensor Function 候補）と BO 目的関数/フィードバックに使う「何を in-line / at-line / offline でどう測れるか」。R&D 文脈。
- 反映先: `../../design/kg_to_auto_cell.md` §4.2、KG `cpv` 拡充。

## 結論サマリ

計測対象ごとに観測性が大きく異なる。**閉ループに使える（in-line/at-line・低遅延）のは VCD・代謝物・（限定的に）凝集体径。
品質（未分化/同一性）と無菌性は offline/run 単位＝BO 目的関数専用**（ただし「offline 限定」は確証 claim 不在に基づく推定で、
低遅延手段の不在を証明したものではない＝要追加調査）。

## 観測性スタック（ICD sensor Function 候補）

### A. 閉ループ制御に使える（in-line/at-line・低遅延）

| 計測 | 手法/機器 | 配置 | cadence | 確度/留保 | 出典 |
|---|---|---|---|---|---|
| **VCD/biomass** | capacitance/誘電分光（Aber FUTURA, Hamilton Incyte Arc, Sartorius BioPAT ViaMass） | **in-line** | ~30s, Modbus 直結 | ✅**Manstein 500mL iPSC で offline VCD と一致（定性, R²なし）**。生細胞特異。iPSC 校正必須（コア壊死/サイズ分布） | PMC8235132, Krause 2023, Hamilton |
| **glucose/lactate/gln/glu** | in-line Raman 分光 | **in-line** | ~1/min | ⚠️CHO 灌流で PID 閉ループ glucose 制御を実証（RMSEP 0.23 g/L）。**iPSC 実証なし＝chemometric 再校正必須** | Graf 2022, Wan 2024 |
| **代謝物16項**（gluc/lac/gln/glu/NH4/Na/K/Ca/pH/PCO2/PO2/総細胞/VCD/生存率/細胞径/osmolality） | Nova BioProfile FLEX2 | **at-line** | ~4.5min/sample, 265-275µL | ✅マルチパラメータ。Raman 校正・灌流補助・BO 入力 | Nova FLEX2 |
| **凝集体径** | in-line DHM（Ovizio iLINE-F PRO; 吸引→解析→無傷返送）/ in-situ FBRM（MT ParticleTrack G400） | in-line/in-situ | 連続 | ⚠️Ovizio は iPSC 実証薄（vote 2-1, FOV/レンジ主張は否決）。**FBRM は弦長分布 CLD≠真の径 PSD・濃度依存** | ChemoMetec, MT G400 |
| **凝集体径（代替）** | bypass flow-chamber 画像（Kropp 2019）/ FlowCam フローイメージング | **at-line** | 24h（研究）/ 離散 | ✅iPSC 実測 50→120→260µm。槽サイズ非依存でスケーラブル | Kropp 2019, FlowCam |
| pH/DO/温度/osmolality | 標準プローブ / Nova(osmolality) | in-line/at-line | 連続/~4.5min | L0 局所 PID＋監督 | （標準） |

### B. BO 目的関数専用（offline/run 単位・低遅延閉ループ不可）

| 計測 | 手法 | 配置 | 留保 |
|---|---|---|---|
| 未分化/多能性マーカー（OCT4/SOX2/NANOG/SSEA/TRA） | フローサイト/qPCR/IF | offline | DR で確証 claim ゼロ＝「offline 限定」は**推定**（不在の証明でない, 要追加調査） |
| 核型/同一性 | 核型/STR | offline | run 単位 |
| 自発分化/形態 | label-free 画像 DL（CellXpress.ai 等） | at-line/offline | ラベルフリー代理指標は将来 in-line 化の余地、現状未確証 |
| 生存率 | Nova(viability) / 画像 | at-line | Nova FLEX2 が viability も測る（A に重複） |
| 無菌/汚染 | rapid micro / online 検知 | offline/rapid | DR で確証 claim ゼロ＝有効な online 手段未確認、**要別途調査**（#17 open） |

## 設計含意

1. **VCD は in-line capacitance が anchor**（Manstein iPSC で検証済, 定性）→ **灌流レバーの閉ループは capacitance-VCD で組める**。§4 VCD channel = capacitance を裏付け。
2. **代謝物は in-line Raman（閉ループ）＋ at-line Nova FLEX2（リッチ panel）**の二段。glucose/lactate 閉ループは Raman で可（iPSC 校正前提）。
3. **凝集体径は turnkey な iPSC 実証 in-line が無い**。v1 は **at-line 画像（Kropp/FlowCam, 日次〜離散）** か **FBRM(CLD プロキシ)** が現実的。§8#3「凝集体径=analog channel（device 算出）」は維持だが**cadence は in-line 連続でなく at-line 寄り**になる前提。
4. **品質/無菌は offline/run 単位 → BO 目的関数の側**。これは ADR-0001 の L1(物理 CPP の決定的制御)/L2(BO は run 結果の品質を最適化) 分離を**裏付ける**: run 内制御は VCD/代謝物/凝集体/pH/DO（観測可能）で回し、品質は run 成果として BO が最適化。

## Caveats（DR 由来 + 検証）

- **iPSC 特異性ギャップ**: Raman 閉ループと capacitance 成熟度の強い実証は **CHO/哺乳類生産細胞**。iPSC で確証は Manstein capacitance-VCD 一致（定性, 単一 500mL run, R²未定量）のみ。CHO スペックを iPSC ターンキー精度と読み替えない。
- **品質/無菌は確証 claim ゼロ**: 「offline/BO 専用」は不在ベースの推定 → #11(品質読み出し)・#17(無菌検知)は別途調査が残る。
- **否決済（使わない）**: Ovizio FOV/最大径(0-3)、FBRM 0.5-2000µm レンジ(1-2)、capacitance「完全転用可能」(1-2)/「閉ループ灌流制御 実証済 in-line」(1-2)/「培地・担体に非影響」(0-3)。
- ベンダページ一部 403 → スニペット/PDF/独立販社で検証（一次直読でない）。capacitance(PMC8235132)は私が一次直読で確認済。

## Open（次調査候補）

- iPSC 品質指標で **run 毎に測れるもの**の具体特定（BO 目的関数の構成要素; #11）。
- 閉鎖系 iPSC での無菌/汚染 online/rapid 検知（#17）。
- capacitance-VCD の iPSC 高密度線形性（~35×10⁶/mL）・サイズ分布補正後精度の定量データ。
