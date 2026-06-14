# Knowledge Graph シード（iPS 自動培養ドメイン知識マップ）

京都大学 iPS 細胞研究財団と関連研究を起点に、自動細胞培養ソフトウェア実装に必要な
ドメイン知識を構造化したナレッジグラフの **シード**。auto_cell の設計はこれを一次資料
（research SoT）とする。設計への落とし込みは [`../design/kg_to_auto_cell.md`](../design/kg_to_auto_cell.md)。

- 規模: **77 ノード / 158 エッジ / 8 ドメイン**（root=1, domain=8, concept=47, system=3, player=5, source=13）
- 生成: 2026-06-14（P1/P3/制御権限）＋ 2026-06-15（P5 観測性）

> **P5 観測性 (2026-06-15)**: 計測スタックを `cpv` に拡充（in-line capacitance VCD＝Manstein iPSC で検証 /
> in-line Raman 代謝物 / at-line Nova FLEX2 / 凝集体 at-line 画像; 品質・無菌は offline＝BO 目的関数専用）。
> 詳細: [`research/2026-06-15_P5_observability.md`](research/2026-06-15_P5_observability.md)、設計反映は
> [`../design/kg_to_auto_cell.md`](../design/kg_to_auto_cell.md) §4.2。現在 **77/158 で全整合**。
- 名前空間: `https://tangletech.dev/ips-automation-kg#`（TTL）

> **P1 拡張＋続報 (2026-06-14)**: 浮遊速度論モデルと CPP の文献根拠を調査。**plant_model の真の原典は
> Manstein & Zweigerdt 2021**（`src_manstein`; SCTM 10:1063-1080 / STAR Protocols 2:100988）で、6 定数
> すべて忠実と確定。deep-research 本調査が一旦原典と推定した Galvanauskas 2019（`src_galv`）は近縁の
> 3 項別モデルで、これは誤推定だった（続報の WebFetch で訂正）。追加: `kinetics`/`src_manstein`/`src_galv`/
> `src_borys`/`src_kropp`/`src_traj`。詳細レポートは
> [`research/2026-06-14_P1_kinetics_cpp.md`](research/2026-06-14_P1_kinetics_cpp.md)（冒頭に訂正セクション）、
> 設計反映は [`../design/kg_to_auto_cell.md`](../design/kg_to_auto_cell.md) §4.1/§6。`json` を正本に派生
> （jsonl/csv/ttl）と HTML ビューア埋め込みを再生成済。

> **P3 デバイス IF / 制御権限 (2026-06-14)**: バイオリアクタ本体は **OPC-UA/LADS 第一**（LADS v1.0.0 が
> バイオリアクタを明示モデル化、`src_lads`）、ラボ自動化は **SiLA2 従**、閉鎖ターンキー(Terumo 等)は制御対象外。
> 協業前提では **制御権限を二層分界**（局所 PID＋ブレイン監督, `ctrl_split`）し、**単一デバイスプロファイル/ICD**
> （LADS 情報モデル, `devprofile`）で device 実装と DomainVertical を束ねる。設計反映は
> [`../design/kg_to_auto_cell.md`](../design/kg_to_auto_cell.md) §7.1-7.3/§8。現在 **77/156 で全整合**。

## ファイル

| ファイル | 形式 | 用途 |
|---|---|---|
| `knowledge_graph.json` | 単一 JSON（meta/domains/nodes/edges） | プログラム取り込みの正本。`json.load` 一発で全構造。 |
| `knowledge_graph.jsonl` | 1 行 1 ノード/エッジ（`_kind`） | ストリーム取り込み・埋め込み生成・差分追記向き。 |
| `knowledge_graph.ttl` | RDF/Turtle | SPARQL / トリプルストア取り込み。`:hasSource` `:inDomain` 等の述語付き。 |
| `nodes.csv` | CSV | 表計算・pandas での俯瞰（`id,label,type,domain,domain_label,content,source_count`）。 |
| `edges.csv` | CSV | エッジ一覧（`source,rel,target`）。関係動詞 = 設計上の依存方向。 |
| `sources.csv` / `sources_unique.csv` | CSV | 出典（ノード別 / 重複排除）。各主張の根拠 URL。 |
| `ips_automation_knowledge_map.html` | D3 力学グラフ | 対話的ビューア。ブラウザで直接開く（要ネット: d3 CDN）。 |

## ビューア

```bash
xdg-open docs/knowledge_graph/ips_automation_knowledge_map.html   # or just open in a browser
```

ドメイン凡例クリックでソロ表示、ノードホバーで隣接ハイライト、クリックで詳細＋関係、
検索ボックスで label/content 全文一致、EXPORT で現在のグラフを JSON 出力。

> **バグ修正済み**: 元 HTML は `EDGES` が `{s,t,rel}` 形式なのに d3 `forceLink` が
> `source`/`target` を参照するため初期化時に `missing: undefined` で例外 → 一切描画
> されなかった。`forceSimulation` 直前で `e.source=e.s; e.target=e.t;` を別名付与して
> 修正（`s`/`t` は `adj`・距離関数・詳細パネル・EXPORT が引き続き参照するため温存）。

## 述語（関係動詞）の読み方

`contains`/`has` は構造（root→domain→concept）。それ以外（`feeds` `triggers` `commands`
`evaluates` `constrains` `governs` `optimizes` 等）が **設計上意味のある依存**。これらの
クロスエッジが制御ループとプラグイン境界を規定する → [設計ブリッジ](../design/kg_to_auto_cell.md)参照。
