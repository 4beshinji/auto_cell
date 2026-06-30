# ROADMAP.md 指摘内容の整合性検証

> 目的: `ROADMAP.md` / `docs/design/roadmap.md` に対する既存指摘（設計再検討レポート、追加調査統合レポート、統合設計根拠レポート）が、実際の文書内容と現在のコード状態に対して妥当かを検証する。
> Scope: auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御、Manstein 型灌流 0→7 vvd）
> 前提: ADR-0001、requirements.md、kg_to_auto_cell.md

---

## 1. 検証の枠組み

### 1.1 検証対象文書

| 文書 | 役割 |
|---|---|
| `ROADMAP.md` | プロジェクト・トップレベルの簡易ロードマップ。上位計画へのリンク、4軸評価、短期/中期/長期重点課題を記載。 |
| `docs/design/roadmap.md` | A 層技術ロードマップ。v1/Phase 2/Phase 3 の機能一覧と移行条件を数値化。 |
| `docs/design/design_reconsideration_report.md` | 設計再検討レポート。ADR/KG/ロードマップに対する 22 項の問題・矛盾・ギャップを列挙。 |
| `docs/design/ground_knowledge/additional_investigation_integrated.md` | 6 ドメイン追加調査（MPC/PINN/Raman/CHO→iPSC/Annex22/画像解析）の統合。 |
| `docs/design/ground_knowledge/integrated_report.md` | Agent Swarm 8 エージェント産出物の統合設計根拠レポート。 |

### 1.2 判定基準

| 判定 | 意味 |
|---|---|
| **妥当** | 指摘は文書またはコード状態と照らして正しく、改善・具体化が必要。 |
| **部分妥当** | 指摘の核心は正しいが、`docs/design/roadmap.md` 等で既に言及されている部分あり。要補強。 |
| **既対応** | `docs/design/roadmap.md` または ADR-0001 §9 で既に明確に位置づけ・数値化されている。 |
| **要確認** | 指摘の真偽を追加調査・実装検証で確認する必要がある。 |

---

## 2. 指摘別検証結果

### 2.1 制御アーキテクチャ

| # | 指摘 | ROADMAP.md 状態 | 詳細ロードマップ状態 | コード状態 | 判定 | 備考 |
|---|---|---|---|---|---|---|
| A1 | MPC の将来位置づけが不明確 | ROADMAP.md §3 中期に「多変数適応 MPC」とのみ記載 | roadmap.md §5.1 で Phase 2 シミュレーション→Phase 3 実装と位置づけ済 | 未実装 | **部分妥当** | 大筋は詳細ロードマップで対応。ただし内部モデル・CasADi/do-mpc 等の実装資産は未定。 |
| A2 | L2 BO の探索空間・目的関数・制約が具体化されていない | ROADMAP.md §3 中期に BoTorch/Ax 導入と記載 | roadmap.md §2.1 #4, §3.1 #7 で目的関数具体化を Phase 1/2 課題として言及 | 未実装 | **妥当** | 目的関数の重み、探索空間の型・範囲、制約コードが未策定。 |
| A3 | L3 LLM の Annex 22 分類が文書化されていない | 未言及 | 未言及 | 未実装 | **妥当** | ADR-0001 は非クリティカル用途としているが、Annex 22-ready 文書化が不足。 |
| A4 | 信頼度スコア層が設計に明示されていない | 未言及 | roadmap.md §3.1 #5 で Phase 2 信頼度スコアを言及 | `src/auto_cell/plugins/cell_culture/confidence.py` 未作成 | **妥当** | ADR-0001 §9.3 で追加されたが、ROADMAP.md には反映されていない。 |
| A5 | L0/L1/L2/L3 のインターフェース・状態遷移が具体化されていない | 未言及 | 概要レベル | 未実装 | **妥当** | レシピ DSL、MQTT cmd/ack、承認状態 topic の実装設計が必要。 |

### 2.2 CPP / 制御変数カタログ

| # | 指摘 | ROADMAP.md 状態 | 詳細ロードマップ状態 | kg_to_auto_cell.md 状態 | 判定 | 備考 |
|---|---|---|---|---|---|---|
| C1 | glucose/lactate/osmolality の「制限値」と「トリガ値/早期警戒値」が混同 | 未言及 | 未言及 | §4.0a で目標/制限/早期警戒/トリガを区分 | **部分妥当** | kg_to_auto_cell.md では区別済。ROADMAP.md には反映されていない。 |
| C2 | アンモニアの iPSC ネイティブ閾値が未確定 | 未言及 | roadmap.md §6 U3 で未解決事項として記載 | §4 で監視値・閾値未確定と記載 | **妥当** | 実装可否を分ける未解決事項。追加調査または実験決定が必要。 |
| C3 | 凝集体径に大径凝集体割合（>400 µm）の監視がない | 未言及 | 未言及 | §4 で `large_aggregate_high` イベントとして追加 | **部分妥当** | kg_to_auto_cell.md では対応済。ROADMAP.md 未反映。 |
| C4 | CSPR（Cell-Specific Perfusion Rate）が設計に現れていない | 未言及 | 未言及 | §4 で計算値として追加 | **部分妥当** | 概念追加済だが、L1/L2 への組み込み方は未定。 |
| C5 | ramp 制限値の文献裏付けが弱い | 未言及 | 未言及 | §4.0a で「初期仮説」と明記 | **妥当** | シア/浸透圧ショック回避の定量的根拠を追加調査。 |

### 2.3 観測性スタック

| # | 指摘 | ROADMAP.md 状態 | 詳細ロードマップ状態 | 追加調査統合 | 判定 | 備考 |
|---|---|---|---|---|---|---|
| O1 | 品質マーカー・無菌性が offline/run 単位のみ | 未言及 | roadmap.md §3.1 #6 で at-line 品質代理指標調査を Phase 2 に配置 | §4.2, §5.1 で offline 制約と位置づけ | **部分妥当** | 設計上の弱点として認識済。at-line 代理指標の調査計画はあるが具体的手法未定。 |
| O2 | Raman 校正戦略の設計文書への反映が不十分 | ROADMAP.md §3 長期に「Raman 閉loop」とのみ記載 | roadmap.md §2.1 #7, §3.1 #3 で v1 観測→v1.5 アドバイザリ→v2 閉loop と段階化 | §4 で詳細な v1/v2 ロードマップを記載 | **部分妥当** | 詳細ロードマップ・追加調査で対応。ROADMAP.md には段階が簡略化されすぎ。 |
| O3 | 凝集体画像の at-line 日次 cadence と L1 イベント設計の整合が不明確 | 未言及 | roadmap.md §2.1 #4 で日次 cadence を言及 | §7.1, §7.2 で at-line 画像を v1 必須と位置づけ | **部分妥当** | 概念は整理済。イベント発火条件・遅延許容の実装設計が必要。 |

### 2.4 デバイス IF / LADS / SiLA2 / MQTT

| # | 指摘 | ROADMAP.md 状態 | 詳細ロードマップ状態 | kg_to_auto_cell.md 状態 | 判定 | 備考 |
|---|---|---|---|---|---|---|
| D1 | MQTT topic 契約に承認状態・HMI 通知 topic が明示されていない | 未言及 | 未言及 | §7.3 で `state/approval/{request_id}`、`notify/hmi/{priority}` を追加 | **部分妥当** | kg_to_auto_cell.md では対応済。ROADMAP.md 未反映。 |
| D2 | LADS Program/Result と EBR/event_store の対応が概念レベル | 未言及 | 未言及 | §7.1, §7.3 で対応関係を記載 | **部分妥当** | 概念対応は示されているが、スキーマ・ID 体系の実装設計が必要。 |
| D3 | フォールバック梯子（LADS 不可時）の v1 実装範囲が未定 | 未言及 | 未言及 | §7.3 で梯子を設計 | **妥当** | v1 では OPC-UA/LADS 第一とするが、Sparkplug B/gRPC/REST フォールバックの実装優先度未定。 |

### 2.5 規制・GMP / Annex 22

| # | 指摘 | ROADMAP.md 状態 | 詳細ロードマップ状態 | 追加調査統合 | 判定 | 備考 |
|---|---|---|---|---|---|---|
| R1 | Annex 22-ready 技術的統制（Intended Use、データ分離、職員独立性、静的決定論的証明、XAI、信頼度、ドリフト監視）が未整備 | ROADMAP.md §3 長期に GMP/Part11/ALCOA+ と記載 | roadmap.md §3.1 #4, #5, #6 で静的決定論的証明・信頼度スコア・ドリフト監視を Phase 2/3 に配置 | §6 で 5 本柱を提言 | **妥当** | 概念レベル。実装スキーマ・CI テスト・テンプレートが未策定。 |
| R2 | 「クリティカル用途」の定義と境界が文書化されていない | 未言及 | 未言及 | §6.3 で L0–L3 と Annex 22 の対応表を作成 | **部分妥当** | 追加調査で対応。設計文書への正式反映が必要。 |
| R3 | XAI/信頼度スコアの実装方針が L2 BO の GP 事後分散に留まり、Raman PLS・画像 DL への適用が未定 | 未言及 | roadmap.md §3.1 #5 で GP 事後分散からの信頼度を言及 | §6.4 で PLS Q 残差/Hotelling T²、DL 予測不確実性を言及 | **妥当** | 各モデルタイプごとの信頼度計算実装方針が未策定。 |

### 2.6 技術ロードマップ

| # | 指摘 | ROADMAP.md 状態 | 詳細ロードマップ状態 | 判定 | 備考 |
|---|---|---|---|---|---|
| T1 | Phase 2/3 の移行条件が数値化されていない | 未言及 | ** roadmap.md §2.2, §3.2, §4.2 で数値化済** | **既対応** | run 蓄積数、Manstein 軌道再現性、L1 決定性検証、ALCOA-lite 運用、HITL PoC、Raman データ取得等が数値化されている。 |
| T2 | BO 目的関数の重みが未決定 | 未言及 | roadmap.md §6 U1 で未解決事項として記載 | **妥当** | 研究者ヒアリングが必要。 |
| T3 | v1/Phase1/Phase2/Phase3 の機能分割は現実的だが未解決事項の優先順位が不明確 | 未言及 | roadmap.md §6 で未解決事項を時期別に記載 | **既対応** | 優先度と時期が整理されている。 |

### 2.7 実装状態

| # | 指摘 | コード状態 | 判定 | 備考 |
|---|---|---|---|---|
| I1 | `sim/plant_model/__init__.py` に Manstein ODE が未実装 | docstring のみ | **妥当** | ROADMAP.md §3 短期 #1 で明記。最優先実装アセット。 |
| I2 | `src/auto_cell/plugins/cell_culture/` にドメインプラグイン未実装 | docstring のみ | **妥当** | ROADMAP.md §3 短期 #3 で明記。environment/channels/events/tools/sanitizer 未作成。 |
| I3 | `infra/virtual_edge/` 未作成 | ディレクトリ不在 | **妥当** | ROADMAP.md §3 短期 #2 で明記。MQTT 仮想バイオリアクター未構築。 |
| I4 | L1/L2 制御エンジン未実装 | 不在 | **妥当** | ROADMAP.md §2 主要な不足点に明記。 |
| I5 | HMI・承認フロー未実装 | 不在 | **妥当** | ROADMAP.md §2 主要な不足点に明記。 |

---

## 3. 総合評価

### 3.1 ROADMAP.md 自体の評価

`ROADMAP.md` は **プロジェクト全体の方向性を示す簡易ロードマップ**として機能しているが、**閉ループ実現に必要な技術資産の具体性に欠ける**。特に以下の点で指摘は妥当:

- **抽象度が高すぎる**: 「多変数適応 MPC」「Raman 閉ループ」「L1/L2 制御エンジン」等が単語レベルで並んでいるが、内部モデル・入出力・状態遷移・承認フローが未定。
- **実装資産との紐付けが弱い**: どのファイル・モジュール・テストが必要かが明確でない。
- **規制・信頼度・XAI 層が省略されている**: ADR-0001 §9.3 で追加された信頼度スコア層が ROADMAP.md に未反映。
- **移行条件の数値化は詳細ロードマップで対応済**: `docs/design/roadmap.md` は比較的具体的だが、`ROADMAP.md` 読者は詳細文書を参照しないと数値基準が見えない。

### 3.2 詳細ロードマップ（`docs/design/roadmap.md`）の評価

詳細ロードマップは **移行条件の数値化、フェーズ機能分割、未解決事項の時期別整理**において指摘の多くを吸収している。ただし、以下は未対応または実装設計レベルで不足:

- L1 レシピ DSL / 状態機械の文法
- L2 BO の探索空間・目的関数・制約のコード化
- MQTT topic 契約（承認状態・HMI 通知）の実装設計
- LADS/SiLA2 gateway のエラーハンドリング・冪等性設計
- 信頼度スコア層の各モデルタイプ別実装方針
- Annex 22-ready 技術的統制の CI 化方針

### 3.3 コード状態の評価

現時点では **設計文書は充実しているが実行可能なコード資産がほぼない**。

| 領域 | 実装率（推定） | 備考 |
|---|---|---|
| Tier2 plant_model | 0% | docstring のみ |
| cell_culture plugin | 0% | docstring のみ |
| infra/virtual_edge | 0% | ディレクトリ不在 |
| L1 決定制御 | 0% | 不在 |
| L2 BO | 0% | 不在 |
| L3 LLM オーケストレータ | 0% | 不在 |
| HMI/承認フロー | 0% | 不在 |
| 監査/ALCOA-lite | 0% | 不在 |
| テスト | 5% | smoke test のみ |

---

## 4. 結論: 指摘の妥当性まとめ

| カテゴリ | 指摘数 | 妥当 | 部分妥当 | 既対応 | 要確認 |
|---|---|---|---|---|---|
| 制御アーキテクチャ | 5 | 3 | 2 | 0 | 0 |
| CPP / 制御変数 | 5 | 2 | 3 | 0 | 0 |
| 観測性スタック | 3 | 0 | 3 | 0 | 0 |
| デバイス IF / MQTT | 3 | 1 | 2 | 0 | 0 |
| 規制・Annex 22 | 3 | 2 | 1 | 0 | 0 |
| 技術ロードマップ | 3 | 1 | 0 | 2 | 0 |
| 実装状態 | 5 | 5 | 0 | 0 | 0 |
| **合計** | **27** | **14** | **11** | **2** | **0** |

**結論**: 指摘の **大多数（25/27 = 93%）が妥当または部分妥当**である。`docs/design/roadmap.md` と `kg_to_auto_cell.md` で既に対応されている項目もあるが、ROADMAP.md 読者や実装者にとっては具体性が不足。特に **L1 DSL、L2 BO コード化、MQTT 承認トピック、信頼度スコア層、Annex 22 技術的統制** は実装計画に盛り込む必要がある。

---

## 5. 参照

- `ROADMAP.md`
- `docs/design/roadmap.md`
- `docs/design/design_reconsideration_report.md`
- `docs/design/ground_knowledge/additional_investigation_integrated.md`
- `docs/design/ground_knowledge/integrated_report.md`
- `docs/design/kg_to_auto_cell.md`
- `docs/design/adr/0001-control-architecture.md`
- `docs/design/requirements.md`
