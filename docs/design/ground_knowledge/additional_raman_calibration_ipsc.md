# iPSC 浮遊/凝集体バイオリアクターにおける Raman 校正戦略

> **担当**: Raman calibration for iPSC suspension（追加調査 Agent Swarm）  
> **作成日**: 2026-06-16  
> **スコープ**: auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御、Manstein 型灌流 0→7 vvd、目標密度 ~35×10⁶ cells/mL）  
> **前提**: ADR-0001（L0 局所 PID + L1 決定的レシピ/ルール + L2 ベイズ最適化 + L3 薄い LLM オーケストレータ）、Human-on-the-loop、R&D 一次

---

## 1. Executive Summary

本調査は、`docs/design/additional_tasks_memo.md` における「iPSC 浮遊培養での Raman 校正戦略」の調査観点に従い、**iPSC 浮遊/凝集体培養への in-line Raman 適用性と校正計画**を補完するものである。

結論:

1. **in-line Raman は TRL 8-9（CHO/mAb 産業）だが、iPSC 浮遊凝集体への実証は限定的**〔事実：Abu-Absi 2011; Costa 2024〕。レポートの楽観的評価をそのまま iPSC に転用できない。
2. **iPSC 特異的な再校正が必須**〔推定〕：培地組成、代謝物濃度範囲、凝集体サイズ、細胞密度、シア感受性が CHO と大きく異なる（Manstein 2021; Kropp 2016）。
3. **校正戦略は「Nova FLEX2 正解ラベル + capacitance VCD + Raman スペクトル」の三軸**〔提案〕：Raman はグルコース/乳酸/グルタミンの in-line 推定、capacitance は VCD anchor、Nova は多パラメータ正解・リファレンス。
4. **凝集体と高密度細胞懸濁液による光散乱（Mie 散乱）が Raman 強度を減衰させ、PLS モデル精度を低下させる**〔事実：Yang 2024; Iversen 2014〕。細胞密度補正またはスペクトル前処理が必要。
5. **PLS モデル構築には 5–15 バッチ、外挿頑健性確保には 10 バッチ以上が目安**〔事実/推定：bioprocesstools.com; Yan 2024〕。3–5 バッチは初期実証にとどまる。
6. **CHO 由来の chemometric モデルは iPSC に直接転用できない**〔推定〕：メディアマトリックス、代謝プロファイル、凝集体光学的特性が異なる。クローン間転移すら困難な事例が報告されている（Machleidt 2024; Pétillot 2020）。
7. **auto_cell v1 では Raman は「Nova FLEX2 校正済み後のオプション/後段」、v2 以降の閉ループ入力昇格を目指す**〔提案〕。Human-on-the-loop、ALCOA-lite ログ、モデルライフサイクル管理を前提とする。

---

## 2. 背景と調査観点

### 2.1 背景

- ダウンロードレポート（`/home/sin/Downloads/report/report.md`）は in-line Raman を TRL 8-9 と評価し、6–10 アナライト同時定量、5–15 バッチキャリブレーション、Yokogawa の glucose RMSEP 0.23 g/L・乳酸 0.29 g/L を強調した。
- auto_cell 設計は、iPSC 浮遊/凝集体プロセスへの実証不足を留保し、v1 では at-line Nova FLEX2 を必須、Raman をオプション/後段と位置づけている（`kg_to_auto_cell.md` §4.2、§5.1）。
- 本調査は、この**相違・ギャップ**を補完する。

### 2.2 調査観点

1. iPSC 浮遊/凝集体培養における Raman 適用事例
2. capacitance/Raman/Nova FLEX2 の組み合わせ校正戦略
3. 凝集体・細胞密度による光散乱の影響
4. PLS モデル構築に必要なバッチ数・校正設計
5. CHO 由来モデルから iPSC への転移可能性

---

## 3. iPSC 浮遊/凝集体培養における Raman 適用事例

### 3.1 哺乳類細胞培養一般の実績（CHO/HEK293/mAb）

| 研究 | 対象 | 計測対象 | 主な成果 | 出典 |
|---|---|---|---|---|
| Abu-Absi et al. 2011 | CHO fed-batch（3 L/15 L） | glucose, lactate, glutamine, glutamate, ammonium, VCD, TCD | in-line Raman による複数パラメータ同時予測の技術的可行性を初めて実証 | DOI 10.1002/bit.23023 |
| Berry et al. 2015 | CHO | growth, metabolites | スケール横断的な Raman 予測モデル | DOI 10.1002/btpr.2035 |
| Matthews et al. 2016 | CHO fed-batch | glucose, lactate | Raman ベース乳酸閉ループ制御。RMSEP glucose 0.27 g/L、lactate 0.20 g/L | DOI 10.1002/bit.26018 |
| Santos et al. 2018 | CHO mAb | metabolites, titer | 産業利用に向けた Raman PAT ツールの信頼性評価 | DOI 10.1002/btpr.2635 |
| Müller et al. 2024 | CHO | multiple | Indirect Hard Modeling (IHM) によるロバストモデル | DOI 10.1002/bit.28724 |
| Graf et al. 2022 | CHO 灌流 | glucose | Raman による灌流培養の非侵襲連続制御 | DOI 10.3389/fbioe.2022.719614 |

**解釈**: これらは**CHO/mAb 由来**の実績であり、iPSC 浮遊凝集体への直接的適用を保証するものではない〔事実/推定〕。

### 3.2 iPSC/hPSC への適用

| 研究/レビュー | 対象 | 主張 | 出典 |
|---|---|---|---|
| Costa et al. 2024 | cell therapy bioprocessing（包括レビュー） | Raman は細胞密度、生存率、代謝物、細胞同一性バイオマーカーの同時計測に潜在力。ただし iPSC 浮遊培養への in-line 実装例は限定 | DOI 10.1016/j.biotechadv.2024.108166 |
| Polanco et al. 2020（Trends Biotechnol） | iPSC 品質維持技術 | Raman/NIR は代謝物モニタリングの有望な online probe。凝集体形成の再現性と多能性維持がスケーラビリティの鍵 | DOI 10.1016/j.tibtech.2020.04.006 |
| Isidro et al. 2021 | hiPSC 拡大・肝分化（3D） | **dielectric spectroscopy（capacitance）**による online monitoring。Raman は直接使われず、capacitance が VCD 推定に用いられた | DOI 10.1002/bit.27751 |
| Manstein et al. 2021 | hPSC 灌流撹拌槽 | pH/DO/glucose/lactate/osmolality を制御。in-line Raman は使用せず、at-line/off-line 解析で代謝物を追跡 | DOI 10.1002/sctm.20-0453, PMID 33660952 |

**解釈**: iPSC/hPSC の**浮遊凝集体培養そのもの**に in-line Raman を適用した実証研究は、公開文献では**稀または未確定**である〔推定/未確定〕。したがって、レポートの「TRL 8-9」評価は CHO/mAb 文脈であり、iPSC では低く見積もる必要がある〔推定〕。

### 3.3 ベンダー事例

| ベンダー/技術 | 主張 | 出典 |
|---|---|---|
| Yokogawa Electric + 関西学院大学 | 培地データからの Raman 校正モデル。glucose RMSEP 0.23 g/L、lactate 0.29 g/L、antibody 0.20 g/L | Spectroscopy Online 2026-05-20（原論文は確認中） |
| Time-Gated Raman（Timegate） | 蛍光妨害を抑制し、発酵/細胞培養プロセスを monitor。酵母発酵で glucose/ethanol 定量が可能 | timegate.com アプリケーションノート |
| Repligen MAVERICK | de novo モデルによる glucose/lactate/biomass 計測。複数哺乳類培地で検証 | Repligen DOC043_1.PDF |
| Metrohm 2060 Raman | cell culture bioreactor の glucose/lactate in-line 計測。SEP glucose 0.20 g/L、lactate 0.12 g/L | Metrohm AN-PAN-1065 |

**解釈**: ベンダー事例も CHO/HEK293/発酵が中心。iPSC 凝集体マトリックスに対する検証は謳われていない〔推定〕。

---

## 4. capacitance/Raman/Nova FLEX2 の組み合わせ校正戦略

### 4.1 各センサの役割分担（A 層向け）

| センサ | 計測対象 | A 層での役割 | cadence | 信頼度 |
|---|---|---|---|---|
| **in-line capacitance**（Aber FUTURA / Hamilton Incyte） | VCD/biomass | 灌流/継代トリガの anchor | ~30 s | Manstein iPSC で定性的一致。細胞株毎再校正必要〔事実/推定〕 |
| **in-line Raman** | glucose, lactate, glutamine（+ glutamate/ammonia） | 代謝物の in-line 推定、灌流/給餌トリガ | ~1 min | CHO で実証。iPSC では再校正必須〔推定〕 |
| **at-line Nova FLEX2** | 16 項代謝物 + osmolality + viability + 細胞径 + NH4+ | Raman 校正の正解ラベル、BO 入力、リファレンス | ~4.5 min（サンプリング含む） | 産業標準 at-line〔事実〕 |
| **at-line 凝集体画像** | 凝集体径/形態 | 品質・継代判断の代理指標 | 日次〜条件起動 | v1 標準〔提案〕 |

### 4.2 組み合わせ校正戦略

**三軸校正フレームワーク**〔提案〕：

1. **Raman ↔ Nova FLEX2 校正**: Nova による offline 参照値を正解ラベルとし、PLS 回帰で Raman スペクトルから glucose/lactate/glutamine を推定。
2. **capacitance ↔ offline VCD 校正**: Raman の VCD 推定は精度が低い傾向（R² 0.85–0.93）ため、VCD anchor は capacitance が主〔事実：bioprocesstools.com〕。
3. **凝集体画像 ↔ Raman 干渉補正**: 凝集体径・密度を光散乱補正の共変量として利用（後述）。

### 4.3 校正ワークフロー（推定）

```
Phase 0: 機器準備
  - Raman プローブ（785 nm 標準）の設置、滅菌サイクル確認
  - capacitance プローブの設置、2 点校正
  - Nova FLEX2 MicroSensor Card 校正、カートリッジ交換記録

Phase 1: ベースラインデータ取得（3–5 バッチ）
  - iPSC 浮遊灌流 run を実施
  - 4–8 h 間隔で Nova サンプリング
  - 各サンプル時刻に対応する Raman スペクトル・capacitance 値・凝集体径を記録
  - ALCOA-lite: run_id, timestamp, operator, probe_id, lot, calibration version をログ

Phase 2: PLS モデル構築
  - 前処理: ベースライン補正、Savitzky-Golay 微分、SNV/MSC
  - 変数選択: glucose 400–550/1000–1200 cm⁻¹、lactate 840–870 cm⁻¹
  - 留一バッチアウト交差検証で LV 数決定（代謝物 3–8 LV）
  - 外部検証: 独立 2–3 バッチで RMSEP、R²、bias を評価

Phase 3: 光散乱補正
  - 細胞密度・凝集体径を共変量に含めた補正項を追加
  - または Yang et al. 2024 型の cell-scattering correction を適用

Phase 4: 運用・ライフサイクル管理
  - 新規培地ロット、細胞株変更、スケール変更時に再校正トリガ
  - Human-on-the-loop: 低信頼度時は Nova 値を優先
```

---

## 5. 凝集体・細胞密度による光散乱の影響

### 5.1 光散乱のメカニズム

- Raman プローブは懸濁細胞/凝集体による **Mie 散乱**を受け、**Raman 強度が減衰**する〔事実：Yang 2024; Thompson thesis〕。
- 散乱の影響は Beer-Lambert 則では記述できず、細胞濃度と非線形な関係を示す〔事実：Yang 2024〕。
- 細胞サイズ（凝集体径 150–350 µm）は可視・近赤外レーザー波長（785 nm）と比較して大きく、複雑な散乱パターンを生じる〔推定：Thompson thesis; Mie theory〕。

### 5.2 補正戦略

| 戦略 | 詳細 | 出典 |
|---|---|---|
| **SNV/MSC 前処理** | 乗法的散乱効果を正規化 | bioprocesstools.com; Wold 2001 |
| **内部標準（水ピーク 1600–1700 cm⁻¹）** | 水ピーク強度で散乱減衰を補正 | Iversen 2014 |
| **細胞密度共変量** | VCD/capacitance を PLS モデルに追加 | 推定 |
| **cell-scattering correction 式** | Log(R_cell) = a × C^b で減衰比をフィット | Yang 2024 |
| **2nd derivative 前処理** | VCD 予測で 1st derivative より良好 | Mehta 2024 |

### 5.3 iPSC 凝集体特有の留意点

- 凝集体径は培養日数とともに増大（Eppendorf SciVario 例：95 µm → 530 µm）〔事実：Eppendorf AN485〕。
- 凝集体径の増大は光路長・散乱断面積を変化させ、Raman 信号強度に日次変動をもたらす可能性がある〔推定〕。
- StemCell Technologies 推奨では、多能性維持のため凝集体径は **400 µm 以下**が望ましい〔事実：StemCell mTeSR 3D マニュアル〕。これは光散乱の上限にも対応する。

---

## 6. PLS モデル構築に必要なバッチ数・校正設計

### 6.1 バッチ数目安

| 目的 | 推奨バッチ数 | 根拠 |
|---|---|---|
| 初期実証 | 3–5 バッチ | 推定；範囲内の濃度変動をカバー |
| ロバストモデル | 5–15 バッチ | 事実/推定：bioprocesstools.com; alignment メモ |
| スケール/クローン間転移 | 10 バッチ以上 | 推定：Yan 2024; Rowland-Jones 2021 |

### 6.2 Yan et al. 2024 の示唆

- 商業規模 CHO 培養での in-line Raman 法開発。
- **測定チャネル数とバッチ数がモデル性能に影響**。多チャネル・多バッチで頑健性向上。
- DOI 10.1002/biot.202300395

### 6.3 校正設計（推定）

- **濃度範囲**: glucose 0.1–6.5 g/L、lactate 0–5 g/L、glutamine 0–4 mM 等、プロセス動態全体をカバー。
- **サンプリング頻度**: 4–8 h 間隔、少なくとも 100 サンプル以上（Yang 2024; bioprocesstools.com）。
- **交差検証**: leave-one-batch-out が標準。
- **外部検証**: 独立バッチ 2–3。
- **性能目標**: RMSEP ≤ 操作範囲の 10%（ICH Q2 基準）、R² ≥ 0.95。

### 6.4 iPSC 浮遊灌流での特殊要因

- 灌流により代謝物濃度が通常の fed-batch より抑えられる（Manstein: glucose >1.5 mM、lactate <50 mM）。
- そのため、低濃度域の分解能が重要となり、サンプリング・Nova 精度がボトルネックになりうる〔推定〕。

---

## 7. CHO 由来モデルから iPSC への転移可能性

### 7.1 転移の制約要因

| 要因 | CHO | iPSC 浮遊凝集体 | 転移への影響 |
|---|---|---|---|
| 培地 | 複雑な化学定義培地（CD-CHO、ExpiCHO 等） | mTeSR、E8 ベース、独自培地 | マトリックススペクトルが異なる〔推定〕 |
| 代謝プロファイル | 抗体産生、乳酸蓄積傾向 | 未分化維持、乳酸再利用、高いグルタミン依存 | ピーク強度・相関構造が異なる〔推定〕 |
| 細胞サイズ/凝集体 | 単一懸濁（~10–20 µm） | 凝集体 150–350 µm | 光散乱・遮蔽効果が大きい〔推定〕 |
| 細胞密度 | 通常 1–3×10⁷ cells/mL 程度 | Manstein: ~3.5×10⁷ cells/mL | 高密度による非線形減衰〔推定〕 |
| 品質指標 | mAb タイトル | 未分化マーカー、多能性 | Raman からの代理推定は未確定〔未確定〕 |

### 7.2 文献的裏付け

- **Pétillot et al. 2020**: Raman モデルのキャリブレーション転移は難しく、Kennard-Stone piecewise direct standardization 等が必要。DOI 10.1002/eng2.12230
- **Machleidt et al. 2024**: CHO クローン間であっても cross-clone Raman モデルは性能が制限される。DOI 10.1002/biot.202300289
- **Rowland-Jones et al. 2021**: ミニバイオリアクタから大規模攪拌槽へのモデル転移は、プローブ/フローセル設計の違いが障壁。DOI 10.1002/btpr.3074

**結論**: CHO モデルを iPSC に転用することは、**技術的に不合理**〔推定〕。iPSC 特異的な校正データセットを新規に構築すべきである。

---

## 8. auto_cell A 層への設計含意

### 8.1 L0–L3 分離との整合

| 層 | Raman 関連の扱い | 備考 |
|---|---|---|
| L0 | Raman プローブはセンサ。制御ループには直接参加しない | 安全/秒オーダー PID はプローブに依存しない |
| L1 | Raman 推定値を **glucose_low / lactate_high / glutamine_low** イベントの追加入力として使用可能（校正後） | 決定的ルールで扱う。信頼度スコアでゲート |
| L2 | Raman データを BO の入力特徴量として蓄積。run 間最適化に活用 | 多忠実度 BO の低忠実度は Tier2 plant_model |
| L3 | 低信頼度・外挿時の Human-on-the-loop 承認仲介 | LLM は推定値の説明・警報生成に限定 |

### 8.2 v1/v2 採用ロードマップ

| 段階 | Raman の位置づけ | 条件 |
|---|---|---|
| v1（Phase 1） | **オプション観測**。Nova FLEX2 を正解とする校正計画を策定。Raman 値は記録・表示のみ、制御には使用しない | iPSC 校正データなしの段階 |
| v1.5（Phase 1 後期） | **アドバイザリ入力**。glucose/lactate 推定値を L1 イベントの追加参考情報として提示。制御アクションは人承認 | 5 バッチ以上の校正・外部検証達成後 |
| v2（Phase 2） | **閉ループ入力候補**。校正モデルを `validate_tool_call` の包絡線と組み合わせ、灌流/給餌トリガに使用 | 10 バッチ以上・光散乱補正・再現性確認後 |

### 8.3 データモデル・ALCOA-lite 要件

- 各 Raman 推定値は **信頼度スコア**（Raman モデルの予測分散、PLS の Q 残差、Hotelling T²）を伴う。
- 全校正イベント（サンプル採取時刻、Nova 値、Raman スペクトル ID、モデル version、校正係数、再校正トリガ）は `event_store` に append-only で記録。
- モデル version はレシピ DSL/状態機械の一部として管理し、再現性を保証。

### 8.4 Human-on-the-loop

- **低信頼度時**: Nova 値を優先し、Raman 推定値は参考表示のみ。
- **外挿時**: 校正範囲外の濃度・凝集体径・細胞密度域では、Raman ベースの制御提案を人へ承認要求。
- **再校正トリガ時**: 新規培地ロット、細胞株変更、プローブ交換時は L3/研究者へ通知。

---

## 9. 未確定事項・次ステップ

| # | 項目 | 状態 | 次のアクション |
|---|---|---|---|
| U1 | iPSC 浮遊凝集体における Raman 実証データ | 未確定 | 協業パートナー/ベンダーでの PoC |
| U2 | 凝集体径・密度による光散乱補正の定量式 | 推定 | 標準添加/混合標準実験で a, b パラメータ推定 |
| U3 | Nova FLEX2 vs Raman の時間同期・遅延補正 | 未確定 | サンプリング/測定パイプライン設計 |
| U4 | 培地ロット間・細胞株間のモデル頑健性 | 未確定 | 複数ロット/株での検証バッチ |
| U5 | Raman 推定値の GAMP5/CSV 検証戦略 | 推定 | R&D 一次から GMP-ready への橋渡し文書化 |
| U6 | 低コスト化・複数リアクタ並行校正の効率化 | 推定 | Ambr/ミニバイオリアクタとの連携検討 |

---

## 10. 出典

| ID | タイトル | 出典 | 確度 |
|---|---|---|---|
| Abu-Absi 2011 | Real time monitoring of multiple parameters in mammalian cell culture bioreactors using an in-line Raman spectroscopy probe | DOI 10.1002/bit.23023 | 事実 |
| Matthews 2016 | Closed loop control of lactate concentration in mammalian cell culture by Raman spectroscopy | DOI 10.1002/bit.26018 | 事実 |
| Berry 2015 | Cross-scale predictive modeling of CHO cell culture growth and metabolites using Raman spectroscopy | DOI 10.1002/btpr.2035 | 事実 |
| Yan 2024 | Development of an in-line Raman analytical method for commercial-scale CHO cell culture process monitoring: influence of measurement channels and batch number on model performance | DOI 10.1002/biot.202300395 | 事実 |
| Costa 2024 | Harnessing Raman spectroscopy for cell therapy bioprocessing | DOI 10.1016/j.biotechadv.2024.108166 | 事実 |
| Manstein 2021 | High density bioprocessing of human pluripotent stem cells by metabolic control and in silico modeling | DOI 10.1002/sctm.20-0453, PMID 33660952 | 事実 |
| Yang 2024 | In-line monitoring of bioreactor by Raman spectroscopy: direct use of a standard-based model through cell-scattering correction | J Biotechnol 396:41-52, DOI 10.1016/j.jbiotec.2024.10.007 | 事実 |
| Iversen 2014 | Raman spectroscopy for bioethanol: cell-scattering quadratic correction | 論文参照（Yang 2024 引用） | 事実 |
| Rowland-Jones 2021 | Spectroscopy integration to miniature bioreactors and large scale production bioreactors | DOI 10.1002/btpr.3074 | 事実 |
| Machleidt 2024 | Feasibility and performance of cross-clone Raman calibration models in CHO cultivation | DOI 10.1002/biot.202300289 | 事実 |
| Pétillot 2020 | Calibration transfer for bioprocess Raman monitoring | DOI 10.1002/eng2.12230 | 事実 |
| Graf 2022 | A Novel Approach for Non-Invasive Continuous InLine Control of Perfusion Cell Cultivations by Raman Spectroscopy | DOI 10.3389/fbioe.2022.719614 | 事実 |
| Isidro 2021 | Online monitoring of hiPSC expansion and hepatic differentiation in 3D culture by dielectric spectroscopy | DOI 10.1002/bit.27751 | 事実 |
| bioprocesstools.com | How to Use Raman Spectroscopy for Real-Time Bioprocess Monitoring | https://bioprocesstools.com/blog/raman-spectroscopy-bioprocess-monitoring/ | 推定 |
| Metrohm AN-PAN-1065 | Inline monitoring of cell cultures with Raman spectroscopy | https://www.metrohm.com/en/applications/application-notes/prozess-applikationen-anpan/an-pan-1065.html | 事実 |
| Repligen MAVERICK | Instant Implementation of Raman-Based PAT | https://www.repligen.com/Products/analytics/maverick/Resources/DOC043_1.PDF | 事実 |
| Spectroscopy Online 2026 | Using a New Raman Method for Real-Time Inline Cell Culture Monitoring | https://www.spectroscopyonline.com/view/using-a-new-raman-method-for-real-time-inline-cell-culture-monitoring | 推定 |
| Eppendorf AN485 | Human Induced Pluripotent Stem Cell Aggregate Expansion in Stirred-tank Bioreactors | https://www.eppendorf.com/product-media/doc/en/11804882/Fermentors-Bioreactors_Application-Note_485_SciVario_Human-Induced-Pluripotent-Stem-Cell-hiPSC-Aggregate-Expansion-Stirred-tank-Bioreactors-SciVario-twin-Bioprocess-Controller.pdf | 事実 |
| StemCell mTeSR 3D manual | Expansion of Human Pluripotent Stem Cells as Aggregates in Suspension Culture | https://cdn.stemcell.com/media/files/manual/10000005520-Expansion_of_Human_Pluripotent_Stem_Cells_as_Aggregates_in_Suspension_Culture_Using_mTeSR_3D.pdf | 事実 |
| ADR-0001 | Control architecture — thin LLM orchestrator over deterministic tools + Bayesian optimization | `docs/design/adr/0001-control-architecture.md` | 事実 |
| kg_bridge | KG → auto_cell 設計ブリッジ | `docs/design/kg_to_auto_cell.md` | 事実 |
| alignment | ダウンロードレポートと auto_cell 設計方向性の照合分析 | `docs/design/alignment_with_downloaded_report.md` | 事実 |

---

*本レポートは A 層（iPSC 浮遊/凝集体バイオリアクター制御）に限定。CHO/mAb 由来の数値を iPSC にそのまま転用しないことを明記。*
