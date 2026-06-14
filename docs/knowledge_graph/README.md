# Knowledge Graph シード（iPS 自動培養ドメイン知識マップ）

京都大学 iPS 細胞研究財団と関連研究を起点に、自動細胞培養ソフトウェア実装に必要な
ドメイン知識を構造化したナレッジグラフの **シード**。auto_cell の設計はこれを一次資料
（research SoT）とする。設計への落とし込みは [`../design/kg_to_auto_cell.md`](../design/kg_to_auto_cell.md)。

- 規模: **68 ノード / 139 エッジ / 8 ドメイン**（root=1, domain=8, concept=44, system=3, player=5, source=7）
- 生成: 2026-06-14
- 名前空間: `https://tangletech.dev/ips-automation-kg#`（TTL）

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
