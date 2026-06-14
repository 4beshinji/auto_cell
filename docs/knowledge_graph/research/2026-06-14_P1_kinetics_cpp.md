# P1 調査レポート — 浮遊速度論 ODE の原典と CPP の文献根拠

- 日付: 2026-06-14 ／ 手法: deep-research（5 角度並列検索 → 20 ソース取得 → 98 主張抽出 → 上位 25 を 3 票敵対的検証 → 21 確定 / 4 棄却）
- 対象: auto_cell Tier2 `plant_model` が「published Monod-type ODE を再実装」と主張する**原典の特定**と、A 層 CPP 設定値の文献妥当性。
- 反映先: KG（`kinetics`/`src_manstein`/`src_galv`/`src_borys`/`src_kropp`/`src_traj`）、`docs/design/kg_to_auto_cell.md` §4.1/§6、`sim/plant_model/__init__.py` docstring。

---

## ⚠️ 続報による訂正（2026-06-14, WebFetch — 下記「結論」を一部上書き）

**deep-research 本調査の中心結論（原典 = Galvanauskas 2019・plant_model 要修正）は誤りだった。**
続報の WebFetch（deep-research ハーネス不使用）で **真の原典 = Manstein & Zweigerdt 2021** と判明:

- **Manstein, Ullmann, Triebert & Zweigerdt 2021**: Stem Cells Transl Med 10(7):1063-1080
  (DOI 10.1002/sctm.20-0453, PMID 33660952) ＋ STAR Protocols 2(4):100988 (PMC8666714, Table 1)。
- hPSC **灌流**撹拌槽の Monod 型 in silico モデル。**Table 1 が plant_model の 6 定数すべてと完全一致**:
  µ=1.35/d, K_Glc=1.5mM, K_Lac=50mM, **K_Gln=0.01mM**, **K_Osm=500mOsm/kg**, **K_Agg=350/2=175µm（径）**。
  q_Glc=1.474e-8, q_Lac=2.37e-8, q_Gln=1.856e-9 mmol/cell/d。
- 検証軌道も一致: **70倍・7日・35×10⁶ cells/mL**（150mLで52.5億細胞）、**DO 40→10%**（day6-7）、**pH 7.1**。
- → **plant_model は忠実、定数修正は不要**。決定 (a)（Galvanauskas 値へ揃える）は適用すると正しいモデルを壊すため**棄却**。

**誤りの原因**: deep-research は近縁の Galvanauskas 2019（glucose+lactate+aggregate の **3 項のみ**、
グルタミン/浸透圧を明示的に省略、µmax≈2.35/d）を原典と推定。敵対的検証(3-0)は「Galvanauskas という別
モデルの性質」を正しく確認したが、「それが plant_model の原典である」という**前提自体が未検証**だった。
KGln/KOsm が原典に無いという発見が、むしろ「原典が別にある」サインだった（Manstein には両方ある）。

以下の「結論（判定）」セクションは **deep-research 当時の記録**として残す（1=誤、2=誤の前提に基づく、
4-CPP は有効）。最新の正は本訂正セクションと `docs/design/kg_to_auto_cell.md` §4.1。

---

## 結論（判定）〔deep-research 当時 — §上の訂正で一部上書き〕

1. ~~**原典は特定できた**~~ ❌**誤り（真の原典は Manstein 2021, 上記訂正）**: **Galvanauskas, Simutis, Nath & Kino-Oka, "Kinetic modeling of human induced
   pluripotent stem cell expansion in suspension culture," Regenerative Therapy 2019;12:88-93**
   (DOI 10.1016/j.reth.2019.04.007, PMID 31890771, PMC6933447)。iPSC 浮遊培養（Tic 株 JCRB1331）に
   直接フィットした**ネイティブ Monod モデル**で、CHO 等からの単純転用ではない（vote 3-0）。
   - 式 (Eq.5): `µ = µmax · G/(G+KG) · KLac/(Lac+KLac) · KAgg/(Agg³+KAgg)`
   - 状態変数: 生細胞 / グルコース / 乳酸 / 平均凝集体径 の 4 つ。
   - 構造（グルコース Monod＋乳酸阻害＋凝集体**体積**阻害の 3 項）は plant_model と一致。

2. **plant_model の定数は文献整合とは言えず要修正**:

| 定数 | 現行 plant_model | 原典 Galvanauskas 2019 (Table 1) | 判定 |
|---|---|---|---|
| µmax | 1.35 /day | 0.098 /h ＝ **2.352 /day** | ❌ 不一致 |
| K_Glc | 1.5 mM | 1.27 g/L ＝ **7.05 mM** | ❌ 不一致 |
| K_Lac | 50 mM | 5.0 g/L ＝ 55.5 mM | ✅ 近接 |
| K_Agg | 「175 µm（径）」 | 5.6×10⁶ **µm³（体積）**, ∛≈177.6 µm | ⚠️ 体積を径と誤読 |
| K_Gln | 0.01 mM | **無し**（明示的に省略） | ⚠️ 原典外拡張 |
| K_Osm | 500 mOsm | **無し**（浸透圧変数なし） | ⚠️ 原典外拡張 |

   - 原典逐語:「the glutamine limitation and ammonium inhibition phenomena were neglected and the
     corresponding equations have been omitted」（グルタミン濃度が増殖に有意影響しない範囲に維持、
     アンモニウムは検出限界 0.004 g/L 未満のため）。→ KGln/KOsm は原典に存在しない。

3. **検証軌道「7 日で ~35×10⁶ cells/mL」は近接一次論文で未到達**（vote 3-0）:
   - Nogueira 2019 Vertical-Wheel: peak **2.3×10⁶ cells/mL**（day5, mTeSR1+DS, 約 9.3 倍, µ 1.1±0.2/day）
   - Olmer 2012 撹拌槽: **2.4×10⁶ cells/mL**（day7, 線形増殖, 凝集体径 93-125 µm）
   - 35×10⁶ は約 15 倍高く、強化/灌流など別系統の高度プロセス由来ベンチマーク。**出典未特定**。

4. **CPP の文献妥当性**:
   - **撹拌**: iPSC Vertical-Wheel で **40 rpm が最適**（Borys 2021: day6 で 32.3±3.2 倍、CFD 20-100 rpm）、
     別 DoE（Yehya 2024）も 60→40 rpm へ低減してシア低減。→ auto_cell の **50-120 rpm は上限が高い**、
     最適域はむしろ 40-60 rpm。
   - **凝集体径**: day5 で 169-275 µm、**>400 µm で壊死**（Borys 2021）。→ ターゲット 150-350 µm は妥当
     （原典の体積定数立方根 ≈178 µm もこの範囲内）。✅
   - **pH/DO/給餌**: Kropp/Lipsitz 2015（Box-Behnken DoE）で pH 7.3・毎日給餌で高密度・播種 2×10⁵ が最適、
     **DO は本研究で非有意**。⚠️ ただし HES2(ESC)・Micro-24 **振盪式**（400 rpm は振盪周波数でインペラ rpm/
     P·V へ転用不可）で、iPSC・インペラ撹拌槽への転用に注意。pH 7.3 は目標 7.1 より高い。
   - **浸透圧**: CHO で 382 mOsm/kg 閾値（Xing 2008）— KOsm 500 mOsm と**同オーダーだが別量**（閾値 ≠ 半阻害定数, vote 2-1）。
   - **乳酸**: K_Lac の CHO 由来説は棄却（0-3）。原典 Galvanauskas の ≈55 mM が根拠。

## 棄却された主張（参考）

- 「CHO/hybridoma の K_Lac=43-90 mM が auto_cell の 50 mM をブラケット → 文献整合」: 1-2 棄却。
- 「Xing 2008 の乳酸閾値 58 mM が CHO 由来 K_Lac の出所」: 0-3 棄却。
- 「CHO 浸透圧/乳酸閾値が Monod 方程式で検証され、同じ構造族」: 0-3 棄却。
  → 乳酸/浸透圧定数の **CHO 由来説は否定**。原典は iPSC ネイティブの Galvanauskas。

## 主要ソース（一次）

| 役割 | 文献 | URL |
|---|---|---|
| **ODE 原典** | Galvanauskas et al. 2019, Regen Therapy 12:88-93 | PMC6933447 / pubmed 31890771 |
| 独立参照 | Comm Biol 2024（"Monod-type … developed by Galvanauskas et al." と引用） | PMC10774284 |
| 撹拌/凝集体 CPP | Borys et al. 2021, Stem Cell Res Ther 12:55 | PMC7805206 |
| 撹拌 DoE | Yehya et al. 2024, Stem Cell Res Ther 15:191 | PMC11218057 |
| pH/DO/給餌 DoE | Kropp/Lipsitz et al. 2015, BMC Proceedings | PMC4685349 |
| 到達密度 実測 | Nogueira 2019, J Biol Eng / Olmer 2012, Tissue Eng C | PMC6744632 / PMC3460618 |
| 浸透圧閾値(CHO) | Xing et al. 2008, Biotechnol Prog 24:675 | pubmed 18422365 |
| 非原典（除外） | bioRxiv 2026 VW シア応力 / Bio-SoS(Comm Biol 2024) | — |

## Caveats

1. 原典本文/Table 1 は ScienceDirect/ResearchGate が 403 のため PMC・KTU リポジトリ等のミラーで確認。
   KAgg の単位表記が µm³/mm³ で揺れる箇所があるが、立方根 ≈178 µm が µm³ を支持。load-bearing な結論
   （定数値・per-day 換算・体積 vs 径）はこの揺れの影響を受けない。
2. **KGln/KOsm の具体的数値源は未特定**。原典に無いことは確定だが、CHO 系（Xing 等）からの転用か、
   bioRxiv 2026 が言及する「glucose+lactate+glutamine+osmolality+aggregate を含む**拡張 Monod**」
   （Galvanauskas/Kino-Oka 後続論文の可能性）由来かは未確定 → 後者が真の 6 定数原典の可能性が残る。
3. CPP の pH/DO は ESC(HES2)・Micro-24 振盪式由来を含み、iPSC・インペラ撹拌槽/Vertical-Wheel への
   転用に注意（特に 400 rpm はインペラ速度でなく振盪周波数）。
4. **35×10⁶ cells/mL 軌道の一次出典は本調査では未特定**。質問が挙げた理研/カネカ(林洋平ら eLife)
   一貫化論文・Kanda et al. eLife 2022 の実軌道は検証 21 主張に現れず、別の強化/灌流論文
   （search で 70 倍拡大の PMC8666714 が言及）の可能性。

## 未解決 → P1 続報の調査対象

- KGln/KOsm の数値源（拡張 Monod 後続論文の特定）。これが取れれば 6 定数すべて整合する真の原典が確定。
- 「7 日 35×10⁶ cells/mL、DO 40%→10%」の定量を報告する一次論文の特定。
- KAgg を体積(µm³)として正しく実装するか — 現状コードは ODE 本体未実装（docstring のみ）。実装時に Agg³ 項で体積として扱う。
