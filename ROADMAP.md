# auto_cell ロードマップ

> 本ドキュメントは [`/home/sin/code/agent/auto/ROADMAP.md`](../ROADMAP.md)（上位ロードマップ）の下位計画です。
>
> 目的: ヒト iPS 細胞（hiPSC）の 3D 浮遊凝集体バイオリアクター培養において、センサー・at-line 分析・シミュレータから意思決定を補助・自動化するための充足・不足を整理し、改善ロードマップを示す。

---

## 1. 現状サマリー

| 項目 | 内容 |
|---|---|
| **ドメイン** | iPS 細胞 3D 浮遊/凝集体バイオリアクター灌流培養 |
| **成熟度** | Phase 1 / コア閉ループ実装済み（R&D） |
| **主要な充足点** | `physical-ai-core` への editable 依存採用、ADR-0001 制御アーキテクチャ確定、詳細な設計文書・ナレッジグラフ、GMP/Part 11/ALCOA+ 対応設計、Manstein ODE シミュレータ、`cell_culture` ドメインプラグイン、L1 決定的レシピ/ルールエンジン、ALCOA-lite 監査ログ・承認フロー、MQTT gateway / 仮想バイオリアクター、L2 BO（Ax/BoTorch）骨格、L3 LLM オーケストレータ骨格、凝集体画像解析（Cellpose + scikit-image fallback）骨格、信頼度スコア層骨格 |
| **主要な不足点** | 多変数適応 MPC、Raman 閉ループ、凝集体画像 DL 品質代理指標の実 run 検証、GMP IQ/OQ/PQ・電子署名・完全職員独立性 |

---

## 2. 4 軸評価

| 軸 | スコア | コメント |
|---|---|---|
| 情報源の充実度 | 4/5 | センサー設計・チャネル定義・at-line 計測計画が実装に落ちている。凝集体画像パイプラインは骨格実装済み |
| 意思決定ループ完成度 | 4/5 | L1 決定的閉ループ（Sense→Decide→Act）が plant_model + レシピ/ルールエンジン + 承認フローで成立。L2/L3 は骨格実装済み（L1 統合は Phase 2） |
| シミュレータ・デジタルツイン活用度 | 3/5 | Manstein ODE + 7 日 golden test + E2E 閉ループテストが動作。MPC/PINN/Hybrid DT は未実装 |
| 共通化・統合余地 | **4/5** | `physical-ai-core` 上に構築済みで、他 PJ 資産（business-ops の audit/workflow 等）の流用が容易 |

---

## 3. 重点課題と優先アクション

### 短期（完了 / 1〜2 ヶ月）

- `sim/plant_model/` に Manstein 2021 の 6 項 Monod 型 ODE を実装し、7 日 35×10⁶ cells/mL 軌道を CI で再現する ✅
- `infra/virtual_edge/` を新規作成し、`cell/{culture_unit}/...` MQTT トピックで動作する仮想バイオリアクターを構築する ✅
- `src/auto_cell/plugins/cell_culture/` に `environment.py`, `channels.py`, `events.py`, `tools.py`, `sanitizer.py`, `prompt.py` を実装する ✅
- ALCOA-lite 監査ログ（ハッシュチェーン）と研究者承認フロー（FastAPI）の骨格を導入する ✅
- `src/auto_cell/l2_bayesian/` に Ax/BoTorch ベースの run 間最適化エンジン骨格を導入する ✅
- `src/auto_cell/l3_orchestrator.py` にイベント駆動 LLM オーケストレータ骨格（プロンプトバージョニング + 入出力ログ + ガード）を導入する ✅
- `src/auto_cell/plugins/cell_culture/aggregate_imaging.py` に Cellpose ベースの凝集体画像解析骨格を導入する ✅
- `src/auto_cell/plugins/cell_culture/confidence.py` に GP/PLS/DL 分岐の信頼度スコア層骨格を導入する ✅

### 中期（3〜6 ヶ月）

- L2 ベイズ最適化エンジンを L1 サイクルと統合し、run 間の設定点最適化を開始する
- Nova FLEX2 / LADS / SiLA2 / OPC-UA gateway アダプタを実装し、at-line データを `event_store` に取り込む
- 凝集体画像解析パイプラインを L1/L2 入力に組み込み、径分布・形態メトリクスでイベント発火する
- HMI ダッシュボード UI（backend は完了）を構築する

### 長期（6 ヶ月〜）

- 多変数適応 MPC、Raman 閉ループ、Hybrid ODE+NN / PINN デジタルツインを構築する
- 多忠実度 BO（Tier2 plant_model を低忠実度、実 run を高忠実度）を運用化する
- GMP IQ/OQ/PQ、電子署名、完全職員独立性、WORM 対応を実装する

---

## 4. 既存の詳細ロードマップ

より詳細なフェーズ計画（Phase 1〜3、移行条件、未解決事項）は以下を参照。

- [`docs/design/roadmap.md`](./docs/design/roadmap.md)
- [`docs/design/closed_loop_planning/`](./docs/design/closed_loop_planning/)

---

## 5. 関連文書・ファイル

- 上位ロードマップ: [`/home/sin/code/agent/auto/ROADMAP.md`](../ROADMAP.md)
- 制御アーキテクチャ: `docs/design/adr/0001-control-architecture.md`
- KG 設計ブリッジ: `docs/design/kg_to_auto_cell.md`
- 規制技術統制: `docs/design/regulatory_technical_controls.md`
- plant_model 設計: `docs/design/ground_knowledge/agent_plant_model.md`
- plant_model 実装: `sim/plant_model/`
- cell_culture プラグイン: `src/auto_cell/plugins/cell_culture/`
- L1 エンジン: `src/auto_cell/l1/`
- HMI / 承認: `src/auto_cell/hmi/`
- 監査ログ: `src/auto_cell/audit/`
- MQTT gateway: `src/auto_cell/gateway/`
- 仮想バイオリアクター: `infra/virtual_edge/`
- L2 BO: `src/auto_cell/l2_bayesian/`
- L3 LLM オーケストレータ: `src/auto_cell/l3_orchestrator.py`
- 凝集体画像解析: `src/auto_cell/plugins/cell_culture/aggregate_imaging.py`
- 信頼度スコア: `src/auto_cell/plugins/cell_culture/confidence.py`
- `physical-ai-core` 依存: `pyproject.toml`
