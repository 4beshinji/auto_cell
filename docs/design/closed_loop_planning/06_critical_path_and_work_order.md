# Phase 1 クリティカルパスと作業順序

> 目的: `05_implementation_plan_phase1.md` の 10 スプリントを俯瞰し、閉ループを最短で成立させるクリティカルパスと、並列化可能なワークストリームを特定する。
> 前提: `04_implementation_plan_overview.md`, `05_implementation_plan_phase1.md`

---

## 1. 定義

### 1.1 「閉ループ成立」の定義

Phase 1 のゴールは **virtual_edge 上で 7 日間のシミュレーション run を完了**すること。これを満たす最小条件は:

1. **Sense**: `virtual_edge` 経由で `plant_model` のセンサ値を取得できる。
2. **Decide**: `CellCulturePlugin` のイベント検知 + L1 レシピ/ルールエンジンでアクションを決定できる。
3. **Act**: `virtual_edge` 経由で `plant_model` にアクチュエータ入力を送信できる。
4. **Loop**: 上記を継続的に繰り返し、7 日間の run を完了できる。
5. **Safety/HITL**: 包絡線内アクションは自律、包絡線外/重大アクションは承認または安全側デフォルト。

### 1.2 クリティカルパスの定義

クリティカルパス = 閉ループ成立に **不可欠** かつ **依存関係上最も長い連鎖** を形成するタスク群。これらが遅延すると全体が遅延する。

---

## 2. タスク依存関係グラフ

```
[WP-A: plant_model]
  A1 定数・状態定義
    ▼
  A2 ODE 右辺（perfusion 項除く）
    ▼
  A3 step() IF
    ▼
  A4 perfusion 項
    ▼
  A5 golden test

[WP-B: cell_culture plugin]
  B1 environment.py (CellCultureEnv)
    ▼
  B2 channels.py
    ▼
  B3 events.py
    ▼
  B4 tools.py + sanitizer.py

[WP-C: L1 engine]
  C1 DSL 文法確定
    ▼
  C2 状態機械
    ▼
  C3 ルールエンジン
    ▼
  C4 サイクル実行器

[WP-D: communication / virtual edge]
  D1 MQTT topic 契約
    ▼
  D2 MQTT client
    ▼
  D3 virtual_edge dummy plant
    ▼
  D4 correlation_id + 冪等性

[WP-E: HMI / approval / audit]
  E1 event_store schema
    ▼
  E2 audit_log
    ▼
  E3 approval state machine
    ▼
  E4 dashboard skeleton

[WP-F: BO / LLM / imaging]
  F1 L2 BO skeleton
  F2 L3 LLM skeleton
  F3 aggregate imaging
  F4 confidence score
```

### 2.1 クロスワークストリーム依存

```
A5 ──▶ C4  （plant_model が L1 サイクルの対象）
B4 ──▶ C2  （tools/sanitizer が状態機械で使用）
B4 ──▶ C3  （events がルールエンジンの入力）
C4 ──▶ D3  （L1 サイクルが virtual_edge を介して plant_model と通信）
D4 ──▶ C4  （冪等性が L1 の安全に必要）
E3 ──▶ C4  （承認状態が L1 の実行判定に必要）
E1 ──▶ E2, E3 （event_store が audit/approval の基盤）
F1 ──▶ C4  （BO 提案が L1 に反映。v1 では非必須）
F2 ──▶ E3  （LLM が承認仲介。v1 では非必須）
F3 ──▶ B3  （画像メトリクスが events 入力。v1 では非必須）
F4 ──▶ E3  （信頼度が承認エスカレーション。v1 では非必須）
```

---

## 3. クリティカルパス特定

### 3.1 Phase 1 クリティカルパス（最短閉ループ）

```
A1 → A2 → A3 → A4 → A5
                       ▼
B1 → B2 → B3 → B4 ────┘
                       ▼
C1 → C2 → C3 → C4 ────┘
                       ▼
D1 → D2 → D3 → D4 ────┘
                       ▼
E1 → E2 → E3 ──────────┘
                       ▼
           [7 日間 E2E 閉ループ]
```

**クリティカルパス上のタスク**:

| # | タスク | ワークストリーム | 理由 |
|---|---|---|---|
| 1 | plant_model 定数・状態定義 | A | 全てのシミュレーションの出発点 |
| 2 | ODE 右辺実装 | A | plant_model の中核 |
| 3 | step() IF | A | L1 から呼ばれる唯一の IF |
| 4 | perfusion 項 | A | Manstein プロトコルの主レバー |
| 5 | golden test | A | 目標軌道再現の確認 |
| 6 | CellCultureEnv | B | 全 CPP のデータモデル |
| 7 | channels.py | B | センサ値の取り込み |
| 8 | events.py | B | 状態判断のトリガー |
| 9 | tools.py + sanitizer.py | B | アクション実行と安全検証 |
| 10 | DSL 文法 | C | レシピ実行の前提 |
| 11 | 状態機械 | C | 培養 phase 管理 |
| 12 | ルールエンジン | C | 条件起動ロジック |
| 13 | サイクル実行器 | C | ループを回す主体 |
| 14 | MQTT topic 契約 | D | 通信プロトコル |
| 15 | MQTT client | D | 通信実装 |
| 16 | virtual_edge dummy plant | D | plant_model との橋渡し |
| 17 | correlation_id + 冪等性 | D | 安全・監査のため |
| 18 | event_store schema | E | ログの基盤 |
| 19 | audit_log | E | ALCOA-lite |
| 20 | approval state machine | E | Human-on-the-loop |
| 21 | 7 日間 E2E 閉ループ | 統合 | Phase 1 完了基準 |

### 3.2 非クリティカルパス（並列化可能・後回し可）

| タスク | ワークストリーム | 理由 |
|---|---|---|
| L2 BO 本格実装 | F | v1 では骨格で十分。run 間最適化は閉ループ内動作に直接不要 |
| L3 LLM 本格実装 | F | v1 では承認仲介の stub で可。定常制御には不要 |
| aggregate imaging 高機能化 | F | v1 では手動または簡易解析でも可。L1 イベントは analog channel 経由で取得 |
| confidence score 拡張 | F | v1 では GP 事後分散の骨格のみ |
| dashboard UI 洗練 | E | v1 では API + 簡易 UI で可 |
| LADS/SiLA2 実機接続 | D | v1 では virtual_edge のみで可 |

---

## 4. 自然な作業順序

### 4.1 第 1 波：基盤構築（Week 1–2）

**順序**: A1 → A2 → A3 → A4 → A5 → B1

**並列タスク**:
- C1（DSL 文法確定）
- D1（MQTT topic 契約）
- E1（event_store schema）

**理由**: plant_model がないと L1 サイクルのテストができない。`CellCultureEnv` は plugin 全般の基盤。DSL、MQTT、event_store は並列で設計を進められる。

### 4.2 第 2 波：プラグイン完成（Week 3–4）

**順序**: B1 → B2 → B3 → B4

**並列タスク**:
- A5（golden test 完成）
- C2（状態機械）
- D2（MQTT client）
- E2（audit_log）

**理由**: `events.py` と `tools.py` は L1 状態機械・ルールエンジンの直接入力。並列で状態機械、MQTT client、audit_log を進める。

### 4.3 第 3 波：L1 エンジンと通信（Week 5–6）

**順序**: C2 → C3 → C4、D2 → D3 → D4

**並列タスク**:
- E3（approval state machine）
- F1（L2 BO skeleton）
- F3（aggregate imaging basic）

**理由**: L1 サイクル実行器が plant_model と通信するため、C4 と D3/D4 は同時に成熟させる必要がある。承認ワークフローは L1 実行判定に必要なので同時進行。

### 4.4 第 4 波：統合と HITL（Week 7）

**順序**: C4 + D4 + E3 → 統合テスト

**並列タスク**:
- E4（dashboard skeleton）
- F2（L3 LLM skeleton）
- F4（confidence score skeleton）

**理由**: 承認状態が L1 に組み込まれて初めて HITL 付きの閉ループが回る。dashboard、LLM、confidence はこの段階で骨格を追加。

### 4.5 第 5 波：安定化・E2E・文書化（Week 8–10）

**順序**: 統合テスト → 7 日間 E2E run → 文書化

**並列タスク**:
- F1–F4 の拡充
- 追加テスト・リファクタリング

**理由**: E2E 安定化の間に、BO/LLM/imaging/confidence を v1 品質まで持っていく。

---

## 5. 並列化可能なワークストリーム

| ワークストリーム | 担当想定 | 開始週 | 終了週 | 前提条件 |
|---|---|---|---|---|
| WP-A plant_model | 開発者 1 | Week 1 | Week 2 | なし |
| WP-B cell_culture plugin | 開発者 2 | Week 1 | Week 4 | A1 完了後本格化 |
| WP-C L1 engine | 開発者 3 | Week 2 | Week 6 | B1, C1 完了後本格化 |
| WP-D MQTT/virtual_edge | 開発者 4 | Week 2 | Week 6 | C1, D1 完了後本格化 |
| WP-E HMI/approval/audit | 開発者 5 | Week 2 | Week 7 | E1 完了後本格化 |
| WP-F BO/LLM/imaging/confidence | 開発者 6 | Week 3 | Week 10 | B1, E1 完了後本格化 |

---

## 6. クリティカルパス上のリスクと対応

| # | リスク | 影響 | 対応 |
|---|---|---|---|
| 1 | plant_model の数値安定性 | A5 遅延 → 全体遅延 | Week 1 内に試行。stiff なら LSODA/BDF |
| 2 | physical-ai-core ABC 未確定 | B1, C1 遅延 | Week 0 で仮 IF を定義。core 確定後に差し替え |
| 3 | events と tools のインターフェース不一致 | C2/C3 遅延 | Week 3–4 でインターフェース凍結 |
| 4 | MQTT 非同期 request-response | D4 遅延 → C4 遅延 | まず同期ラッパで実装 |
| 5 | 承認状態と L1 実行の整合 | E3 遅延 → C4 遅延 | 簡易 in-memory 状態機械から開始 |

---

## 7. 推奨するスプリントレビュー基準

| レビュー | 時期 | 確認内容 |
|---|---|---|
| plant_model レビュー | Week 2 終了 | golden test pass、定数・軌道が原典と一致 |
| plugin IF 凍結レビュー | Week 4 終了 | environment/events/tools/sanitizer のインターフェース確定 |
| L1 + MQTT 結合レビュー | Week 6 終了 | L1 サイクルが virtual_edge 経由で plant_model を駆動 |
| HITL レビュー | Week 7 終了 | 承認・拒否・タイムアウトが L1 に反映 |
| Phase 1 完了レビュー | Week 10 終了 | 7 日間 E2E pass、移行条件達成 |

---

## 8. 参照

- `docs/design/closed_loop_planning/05_implementation_plan_phase1.md`
- `docs/design/closed_loop_planning/04_implementation_plan_overview.md`
- `docs/design/closed_loop_planning/03_swarm_findings_integration.md`
