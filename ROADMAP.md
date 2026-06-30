# auto_cell ロードマップ

> 本ドキュメントは [`/home/sin/code/agent/auto/ROADMAP.md`](../ROADMAP.md)（上位ロードマップ）の下位計画です。
>
> 目的: ヒト iPS 細胞（hiPSC）の 3D 浮遊凝集体バイオリアクター培養において、センサー・at-line 分析・シミュレータから意思決定を補助・自動化するための充足・不足を整理し、改善ロードマップを示す。

---

## 1. 現状サマリー

| 項目 | 内容 |
|---|---|
| **ドメイン** | iPS 細胞 3D 浮遊/凝集体バイオリアクター灌流培養 |
| **成熟度** | Phase 0b / 設計・検証段階（R&D） |
| **主要な充足点** | `physical-ai-core` への editable 依存採用、ADR-0001 制御アーキテクチャ確定、詳細な設計文書・ナレッジグラフ、GMP/Part 11/ALCOA+ 対応設計 |
| **主要な不足点** | ドメインプラグイン未実装、Manstein ODE シミュレータ未実装、L1/L2 制御エンジン未実装、`infra/` / `config/` 未作成、HMI・承認フロー未実装 |

---

## 2. 4 軸評価

| 軸 | スコア | コメント |
|---|---|---|
| 情報源の充実度 | 2/5 | センサー設計・at-line 計測計画はあるが、実装・接続が未完了 |
| 意思決定ループ完成度 | 1/5 | 設計のみ。`physical-ai-core` の runner も未実装のためループ未形成 |
| シミュレータ・デジタルツイン活用度 | 1/5 | Manstein ODE は docstring のみ。L1/L2/BO 全て計画段階 |
| 共通化・統合余地 | **4/5** | `physical-ai-core` 上に構築済みで、他 PJ 資産（business-ops の audit/workflow 等）の流用が容易 |

---

## 3. 重点課題と優先アクション

### 短期（1〜2 ヶ月）

- `sim/plant_model/__init__.py` に Manstein 2021 の 6 項 Monod 型 ODE を実装し、7 日 35×10⁶ cells/mL 軌道を CI で再現する
- `infra/virtual_edge/` を新規作成し、`cell/{culture_unit}/...` MQTT トピックで動作する仮想バイオリアクターを構築する
- `src/auto_cell/plugins/cell_culture/` に `environment.py`, `channels.py`, `events.py`, `tools.py`, `sanitizer_rules.py` を実装する
- `business-ops` の `activity-log` / `workflow` を流用し、ALCOA-lite 監査ログと研究者承認フローの骨格を導入する

### 中期（3〜6 ヶ月）

- L1 決定的レシピ/ルールエンジン（state machine）を実装し、Manstein プロトコルを自動実行する
- Nova FLEX2 / LADS / SiLA2 / OPC-UA gateway アダプタを実装し、at-line データを `event_store` に取り込む
- L2 ベイズ最適化エンジン（BoTorch/Ax）を導入し、run 間の設定点最適化を開始する
- HMI（Dashboard backend/frontend）を `business-ops` / `hems` の資産を流用して構築する

### 長期（6 ヶ月〜）

- 多変数適応 MPC、Raman 閉ループ、Hybrid ODE+NN / PINN デジタルツインを構築する
- 多忠実度 BO（Tier2 plant_model を低忠実度、実 run を高忠実度）を運用化する
- GMP IQ/OQ/PQ、電子署名、完全職員独立性、WORM 対応を実装する

---

## 4. 既存の詳細ロードマップ

より詳細なフェーズ計画（Phase 1〜3、移行条件、未解決事項）は以下を参照。

- [`docs/design/roadmap.md`](./docs/design/roadmap.md)

---

## 5. 関連ドキュメント・ファイル

- 上位ロードマップ: [`/home/sin/code/agent/auto/ROADMAP.md`](../ROADMAP.md)
- 制御アーキテクチャ: `docs/design/adr/0001-control-architecture.md`
- KG 設計ブリッジ: `docs/design/kg_to_auto_cell.md`
- 規制技術統制: `docs/design/regulatory_technical_controls.md`
- plant_model 設計: `docs/design/ground_knowledge/agent_plant_model.md`
- 未実装プラグイン: `src/auto_cell/plugins/cell_culture/__init__.py`
- ODE 未実装ファイル: `sim/plant_model/__init__.py`
- `physical-ai-core` 依存: `pyproject.toml`
