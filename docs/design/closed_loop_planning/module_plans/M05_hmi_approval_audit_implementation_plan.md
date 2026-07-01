# M05 HMI / 承認フロー / ALCOA-lite 監査 詳細実装計画

> Scope: auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御）Phase 1
> 目的: `05_implementation_plan_phase1.md` Sprint 7「HMI / 承認フロー / ALCOA-lite」を、ファイル単位・API 単位・テスト単位まで分解し、実装者がそのままコーディングを開始できる計画とする。
> 前提: `05_implementation_plan_phase1.md`, `06_critical_path_and_work_order.md`, `03_swarm_findings_integration.md`, `02_missing_assets_for_closed_loop.md`, `docs/design/kg_to_auto_cell.md` §5 規制・データインテグリティ

---

## 1. ファイル構成

```
src/auto_cell/
├── hmi/
│   ├── __init__.py
│   ├── approval_service.py       # 承認状態機械・キュー・タイムアウト
│   ├── approval_api.py           # FastAPI エンドポイント（承認操作 / ダッシュボード）
│   ├── approval_matrix.py        # tool/条件 → 承認要否・タイムアウト・安全側デフォルト
│   └── dashboard_service.py      # CPP 現在値・トレンド・phase・承認待ち集計
├── audit/
│   ├── __init__.py
│   ├── event_store.py            # 統一イベントスキーマ + JSONL writer
│   ├── audit_log.py              # append-only + 軽量ハッシュチェーン
│   └── tool_executor.py          # 副作用ツール呼び出しの who/when/what/why ラッパ
└── schemas/
    └── audit_events.py           # Event / AuditRecord / ApprovalRequest 共通 Pydantic モデル

tests/
├── test_approval_flow.py         # 承認要求→承認→実行 / 拒否 / タイムアウト E2E
├── test_audit_log.py             # ALCOA-lite: 完全性・ハッシュチェーン・再現性
├── test_tool_executor.py         # 全副作用ツールの監査ログ化
└── test_dashboard_api.py         # ダッシュボード API スモーク

config/
└── approval_matrix.yaml          # 承認要否マトリクス（研究者・PM と合意後コミット）
```

### 1.1 出力先ディレクトリの意味

- `hmi/`: Human-on-the-loop の状態管理と HMI/API サーバー。L1 エンジンから呼ばれる「承認判定」と、研究者が操作する「承認応答」を同じサービスで扱う。
- `audit/`: ALCOA-lite 技術的統制。すべての副作用・承認・テレメトリは `event_store` に統一スキーマで書き込み、`audit_log` はそのうち「誰が・いつ・何を・なぜ」操作したかの改ざん検知可能な部分集合。
- `schemas/audit_events.py`: `hmi` と `audit` と `plugins/cell_culture/tools.py` が共通で import する型定義。循環 import を防ぐため、ここに集約する。

---

## 2. event_store 統一スキーマ（JSON/JSONL）

すべてのサイクルデータは **1 run = 1 JSONL ファイル** に append-only で書き込む。
ファイルパス: `data/event_store/{run_id}/{YYYYMMDD}.jsonl`（運用時はオブジェクトストレージ/WORM にマップ）。

### 2.1 Pydantic スキーマ

```python
# src/auto_cell/schemas/audit_events.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class EventType(str, Enum):
    TELEMETRY = "telemetry"          # センサ/CPP 定期値
    EVENT = "event"                  # L1 detect_events の発火
    COMMAND = "command"              # L1 → gateway への cmd topic
    ACK = "ack"                      # gateway → L1 への ack topic
    APPROVAL = "approval"            # 承認要求・応答・遷移
    TOOL_EXEC = "tool_execution"     # tool_executor による副作用実行
    AUDIT = "audit"                  # ALCOA-lite 監査レコード
    SYSTEM = "system"                # 起動/停止/phase 遷移


class EventHeader(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: Literal["1.0"] = "1.0"
    run_id: str
    correlation_id: str | None = None   # cmd/ack/approval を紐付ける
    parent_event_id: str | None = None  # 派生関係（command → tool_execution）
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str                         # 例: "l1_engine", "approval_service", "hmi_api"
    actor: str                          # 例: "system", "user:tanaka", "llm:v1.2"
    event_type: EventType


class Event(BaseModel):
    """event_store の 1 行。JSONL 保存。"""
    header: EventHeader
    payload: dict[str, Any]


class TelemetryPayload(BaseModel):
    channel: str
    value: float | int | None
    unit: str | None = None
    quality: Literal["good", "suspect", "bad"] = "good"


class CommandPayload(BaseModel):
    tool_name: str
    args: dict[str, Any]
    request_id: str | None = None


class ApprovalPayload(BaseModel):
    request_id: str
    tool_name: str
    params: dict[str, Any]
    state: str                       # requested / approved / rejected / pending_timeout / executed / cancelled
    requested_by: str
    decided_by: str | None = None
    reason: str | None = None
    timeout_sec: float
    safe_default: str | None = None  # timeout 時の動作: "cancel" / "reject" / "hold"
```

### 2.2 JSONL 1 行例

```json
{
  "header": {
    "event_id": "evt_018f...",
    "schema_version": "1.0",
    "run_id": "run_20260630_001",
    "correlation_id": "corr_a1b2c3",
    "parent_event_id": null,
    "timestamp": "2026-06-30T07:37:21.386000+00:00",
    "source": "l1_engine",
    "actor": "system",
    "event_type": "command"
  },
  "payload": {
    "tool_name": "set_perfusion_rate",
    "args": {"vvd": 8.5},
    "request_id": "req_7d8e"
  }
}
```

### 2.3 EventWriter 骨格

```python
# src/auto_cell/audit/event_store.py
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auto_cell.schemas.audit_events import Event, EventHeader, EventType


class EventWriter:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)

    def _path_for(self, run_id: str) -> Path:
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        dir_ = self.base_dir / run_id
        dir_.mkdir(parents=True, exist_ok=True)
        return dir_ / f"{day}.jsonl"

    def write(
        self,
        run_id: str,
        event_type: EventType,
        payload: dict[str, Any],
        *,
        source: str,
        actor: str,
        correlation_id: str | None = None,
        parent_event_id: str | None = None,
    ) -> Event:
        header = EventHeader(
            run_id=run_id,
            event_type=event_type,
            source=source,
            actor=actor,
            correlation_id=correlation_id,
            parent_event_id=parent_event_id,
        )
        event = Event(header=header, payload=payload)
        line = event.model_dump_json(ensure_ascii=False)
        path = self._path_for(run_id)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            os.fsync(f.fileno())
        return event
```

**ALCOA-lite 対応**: `os.fsync` で append の即時永続化を行う。テストでは `tmp_path` を `base_dir` に渡す。

---

## 3. audit_log 実装：append-only + 軽量ハッシュチェーン

### 3.1 設計方針

- `audit_log` は `event_store` の **ビューではなく独立した改ざん検知可能なストリーム**とする。
- 1 run = 1 JSONL ファイル。各行は前の行のハッシュを `prev_hash` に含む。
- ハッシュ対象は `seq`, `run_id`, `timestamp`, `actor`, `action`, `target`, `params`, `reason`, `correlation_id`, `prev_hash` を含む。**ヘッダー部分のみ**を対象にし、`params` 内の float は round-trip 安定な JSON canonicalization で扱う。

### 3.2 Pydantic スキーマ

```python
# src/auto_cell/audit/audit_log.py
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class AuditRecord(BaseModel):
    seq: int
    run_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str                       # who
    action: str                      # what
    target: str                      # 対象 tool / resource
    params: dict[str, Any]           # what detail
    reason: str                      # why
    correlation_id: str | None       # 紐付け
    prev_hash: str
    hash: str


class AuditLog:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self._seq: dict[str, int] = {}
        self._last_hash: dict[str, str] = {}

    def _path(self, run_id: str) -> Path:
        dir_ = self.base_dir / run_id
        dir_.mkdir(parents=True, exist_ok=True)
        return dir_ / "audit.jsonl"

    @staticmethod
    def _canonical(record: dict[str, Any]) -> str:
        return json.dumps(record, sort_keys=True, ensure_ascii=False, default=str)

    def _compute_hash(self, record: dict[str, Any]) -> str:
        return hashlib.sha256(self._canonical(record).encode("utf-8")).hexdigest()

    def append(
        self,
        run_id: str,
        actor: str,
        action: str,
        target: str,
        params: dict[str, Any],
        reason: str,
        correlation_id: str | None = None,
    ) -> AuditRecord:
        seq = self._seq.get(run_id, 0) + 1
        prev_hash = self._last_hash.get(run_id, "0" * 64)
        body = {
            "seq": seq,
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "action": action,
            "target": target,
            "params": params,
            "reason": reason,
            "correlation_id": correlation_id,
            "prev_hash": prev_hash,
        }
        h = self._compute_hash(body)
        record = AuditRecord(**body, hash=h)
        line = record.model_dump_json(ensure_ascii=False)
        path = self._path(run_id)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            os.fsync(f.fileno())
        self._seq[run_id] = seq
        self._last_hash[run_id] = h
        return record

    def verify(self, run_id: str) -> list[str]:
        """チェーンを検証。壊れている seq を返す。空リスト = OK。"""
        broken: list[str] = []
        path = self._path(run_id)
        if not path.exists():
            return broken
        prev_hash = "0" * 64
        with open(path, encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                if record["prev_hash"] != prev_hash:
                    broken.append(f"seq {record['seq']}: prev_hash mismatch")
                body = {k: v for k, v in record.items() if k != "hash"}
                if self._compute_hash(body) != record["hash"]:
                    broken.append(f"seq {record['seq']}: hash mismatch")
                prev_hash = record["hash"]
        return broken
```

### 3.3 ALCOA-lite マッピング

| ALCOA+ | 実装 |
|---|---|
| Attributable | `actor` フィールド + ユーザー ID / LLM バージョン |
| Legible | JSONL + Pydantic スキーマ。可読ツールで開ける |
| Contemporaneous | `datetime.now(timezone.utc)` で生成時刻を即時記録 |
| Original | append-only ファイル。上書き・削除は API 提供しない |
| Accurate | `tool_executor` 経由で実際の引数をそのまま記録 |
| Complete | 全副作用ツール・全承認・全コマンドを event_store + audit_log 両方に記録 |
| Consistent | UTC ISO 8601 + `run_id` 単位の統一スキーマ |
| Enduring | `os.fsync` + WORM オブジェクトストレージ移行を前提 |
| Available | REST API `/hmi/runs/{run_id}/ebr` で閲覧・ダウンロード |

---

## 4. tool_executor ラッパ：who/when/what/why

### 4.1 設計方針

- すべての副作用 tool は `tool_executor.execute(...)` を通す。
- `contextvars` で「現在の actor / correlation_id / run_id / reason」を伝搬し、async 境界を越えて維持する。
- 実行前に承認要否を判定（`approval_matrix.py`）。要承認なら `ApprovalService` に要求を出し、承認されるまで保留する。
- 実行後、`event_store` と `audit_log` に dual-write する。

### 4.2 実装骨格

```python
# src/auto_cell/audit/tool_executor.py
from __future__ import annotations

import contextvars
import uuid
from typing import Any, Awaitable, Callable

from auto_cell.audit.audit_log import AuditLog
from auto_cell.audit.event_store import EventWriter
from auto_cell.hmi.approval_service import ApprovalService, ApprovalState
from auto_cell.hmi.approval_matrix import ApprovalMatrix, Decision

_run_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("run_id")
_actor_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("actor", default="system")
_corr_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("correlation_id", default=None)
_reason_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("reason", default="")


class ToolExecutor:
    def __init__(
        self,
        event_writer: EventWriter,
        audit_log: AuditLog,
        approval_service: ApprovalService,
        matrix: ApprovalMatrix,
        handlers: dict[str, Callable[..., Awaitable[dict[str, Any]]]],
    ):
        self.event_writer = event_writer
        self.audit_log = audit_log
        self.approval_service = approval_service
        self.matrix = matrix
        self.handlers = handlers

    async def execute(
        self,
        tool_name: str,
        params: dict[str, Any],
        *,
        reason: str | None = None,
    ) -> dict[str, Any]:
        run_id = _run_id_ctx.get()
        actor = _actor_ctx.get()
        correlation_id = _corr_ctx.get() or str(uuid.uuid4())
        reason = reason or _reason_ctx.get() or "no reason provided"

        # 1) 承認要否判定
        decision = self.matrix.decide(tool_name, params, run_context={"run_id": run_id})
        if decision.requires_approval:
            req = await self.approval_service.request(
                run_id=run_id,
                tool_name=tool_name,
                params=params,
                requested_by=actor,
                timeout_sec=decision.timeout_sec,
                safe_default=decision.safe_default,
                correlation_id=correlation_id,
                reason=reason,
            )
            if req.state != ApprovalState.APPROVED:
                raise ApprovalRequiredError(req)

        # 2) event_store: tool_execution requested
        evt = self.event_writer.write(
            run_id=run_id,
            event_type="tool_execution",
            payload={"tool_name": tool_name, "params": params, "status": "started"},
            source="tool_executor",
            actor=actor,
            correlation_id=correlation_id,
        )

        # 3) 実際の副作用呼び出し
        handler = self.handlers[tool_name]
        result = await handler(**params)

        # 4) audit_log + event_store completed
        self.audit_log.append(
            run_id=run_id,
            actor=actor,
            action="tool_executed",
            target=tool_name,
            params=params,
            reason=reason,
            correlation_id=correlation_id,
        )
        self.event_writer.write(
            run_id=run_id,
            event_type="tool_execution",
            payload={"tool_name": tool_name, "params": params, "status": "completed", "result": result},
            source="tool_executor",
            actor=actor,
            correlation_id=correlation_id,
            parent_event_id=evt.header.event_id,
        )
        return result


class ApprovalRequiredError(Exception):
    def __init__(self, request):
        self.request = request
```

### 4.3 contextvars セット用ヘルパ

```python
# src/auto_cell/audit/tool_executor.py（続き）
from contextlib import contextmanager


@contextmanager
def execution_context(run_id: str, actor: str, correlation_id: str | None = None, reason: str = ""):
    tokens = [
        _run_id_ctx.set(run_id),
        _actor_ctx.set(actor),
        _corr_ctx.set(correlation_id),
        _reason_ctx.set(reason),
    ]
    try:
        yield
    finally:
        for tok in tokens:
            ctx_var = [_run_id_ctx, _actor_ctx, _corr_ctx, _reason_ctx][tokens.index(tok)]
            ctx_var.reset(tok)
```

---

## 5. 承認状態管理

### 5.1 状態遷移

```
requested
   ├── approved ──▶ executed
   ├── rejected ──▶ cancelled
   └── pending_timeout ──▶ cancelled   (timeout 時の安全側デフォルト)
```

- 状態遷移は **単方向** とする。`executed` / `cancelled` は終了状態。
- `pending_timeout` は「タイムアウト直前・安全側デフォルトを適用済み」のマーカー状態。
- 実際の tool 実行は `ApprovalService.approve()` 呼び出し側、または `ToolExecutor` が `state == APPROVED` を確認して行う。

### 5.2 Pydantic モデル

```python
# src/auto_cell/hmi/approval_service.py
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ApprovalState(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING_TIMEOUT = "pending_timeout"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


class ApprovalRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    correlation_id: str
    tool_name: str
    params: dict[str, Any]
    requested_by: str
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    timeout_sec: float
    safe_default: str  # "cancel" | "reject" | "hold"
    state: ApprovalState = ApprovalState.REQUESTED
    decided_by: str | None = None
    decided_at: datetime | None = None
    decision_reason: str | None = None
```

### 5.3 状態機械サービス

```python
# src/auto_cell/hmi/approval_service.py（続き）
class ApprovalService:
    def __init__(self, event_writer, audit_log, matrix):
        self._requests: dict[str, ApprovalRequest] = {}
        self._timeouts: dict[str, asyncio.Task] = {}
        self.event_writer = event_writer
        self.audit_log = audit_log
        self.matrix = matrix

    async def request(
        self,
        run_id: str,
        tool_name: str,
        params: dict[str, Any],
        requested_by: str,
        timeout_sec: float,
        safe_default: str,
        correlation_id: str,
        reason: str,
    ) -> ApprovalRequest:
        req = ApprovalRequest(
            run_id=run_id,
            correlation_id=correlation_id,
            tool_name=tool_name,
            params=params,
            requested_by=requested_by,
            timeout_sec=timeout_sec,
            safe_default=safe_default,
        )
        self._requests[req.request_id] = req
        self._log(req, "approval_requested", reason)
        self._timeouts[req.request_id] = asyncio.create_task(
            self._timeout_handler(req.request_id, timeout_sec)
        )
        return req

    async def _timeout_handler(self, request_id: str, delay: float):
        await asyncio.sleep(delay)
        req = self._requests.get(request_id)
        if not req or req.state != ApprovalState.REQUESTED:
            return
        # 安全側デフォルト適用
        if req.safe_default in ("cancel", "reject"):
            req.state = ApprovalState.PENDING_TIMEOUT
            self._finalize(req, ApprovalState.CANCELLED, "system", f"timeout safe_default={req.safe_default}")
        elif req.safe_default == "hold":
            req.state = ApprovalState.PENDING_TIMEOUT
            self._log(req, "approval_pending_timeout", "awaiting human decision beyond timeout")

    def approve(self, request_id: str, actor: str, reason: str) -> ApprovalRequest:
        req = self._get_open(request_id)
        self._finalize(req, ApprovalState.APPROVED, actor, reason)
        return req

    def reject(self, request_id: str, actor: str, reason: str) -> ApprovalRequest:
        req = self._get_open(request_id)
        self._finalize(req, ApprovalState.REJECTED, actor, reason)
        return req

    def execute(self, request_id: str, actor: str = "system") -> ApprovalRequest:
        req = self._requests.get(request_id)
        if not req or req.state != ApprovalState.APPROVED:
            raise ValueError("request must be approved before execute")
        req.state = ApprovalState.EXECUTED
        req.decided_by = actor
        req.decided_at = datetime.now(timezone.utc)
        self._log(req, "approval_executed", "tool executed after approval")
        return req

    def _get_open(self, request_id: str) -> ApprovalRequest:
        req = self._requests.get(request_id)
        if not req:
            raise KeyError(request_id)
        if req.state not in (ApprovalState.REQUESTED, ApprovalState.PENDING_TIMEOUT):
            raise ValueError(f"request already finalized: {req.state}")
        return req

    def _finalize(self, req: ApprovalRequest, new_state: ApprovalState, actor: str, reason: str):
        req.state = new_state
        req.decided_by = actor
        req.decided_at = datetime.now(timezone.utc)
        req.decision_reason = reason
        self._cancel_timeout(req.request_id)
        self._log(req, f"approval_{new_state.value}", reason)

    def _cancel_timeout(self, request_id: str):
        task = self._timeouts.pop(request_id, None)
        if task:
            task.cancel()

    def _log(self, req: ApprovalRequest, action: str, reason: str):
        self.event_writer.write(
            run_id=req.run_id,
            event_type="approval",
            payload=req.model_dump(mode="json"),
            source="approval_service",
            actor=req.decided_by or req.requested_by,
            correlation_id=req.correlation_id,
        )
        self.audit_log.append(
            run_id=req.run_id,
            actor=req.decided_by or req.requested_by,
            action=action,
            target=req.tool_name,
            params=req.params,
            reason=reason,
            correlation_id=req.correlation_id,
        )

    def list_pending(self) -> list[ApprovalRequest]:
        return [r for r in self._requests.values() if r.state == ApprovalState.REQUESTED]
```

---

## 6. 承認キュー API

### 6.1 FastAPI エンドポイント

```python
# src/auto_cell/hmi/approval_api.py
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from auto_cell.hmi.approval_service import ApprovalService, ApprovalRequest
from auto_cell.audit.event_store import EventWriter
from auto_cell.audit.audit_log import AuditLog

app = FastAPI(title="auto_cell HMI API")


def get_services() -> tuple[ApprovalService, EventWriter, AuditLog]:
    # DI コンテナ or シングルトン。実装時は lifespan で初期化。
    ...


class DecisionBody(BaseModel):
    actor: str
    reason: str


@app.get("/hmi/approvals/pending", response_model=list[ApprovalRequest])
async def list_pending():
    svc, _, _ = get_services()
    return svc.list_pending()


@app.get("/hmi/approvals/{request_id}", response_model=ApprovalRequest)
async def get_request(request_id: str):
    svc, _, _ = get_services()
    req = svc._requests.get(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="not found")
    return req


@app.post("/hmi/approvals/{request_id}/approve", response_model=ApprovalRequest)
async def approve(request_id: str, body: DecisionBody):
    svc, _, _ = get_services()
    try:
        return svc.approve(request_id, body.actor, body.reason)
    except KeyError:
        raise HTTPException(status_code=404)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/hmi/approvals/{request_id}/reject", response_model=ApprovalRequest)
async def reject(request_id: str, body: DecisionBody):
    svc, _, _ = get_services()
    try:
        return svc.reject(request_id, body.actor, body.reason)
    except KeyError:
        raise HTTPException(status_code=404)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
```

### 6.2 タイムアウト処理

- `ApprovalService.request()` 内で `asyncio.create_task(self._timeout_handler(...))` を生成。
- 承認/拒否で `task.cancel()`。
- プロセス再起動時は承認待ちが失われる。**Phase 1 では in-memory で許容**し、再起動前に `cancel_all_pending(safe_default)` を呼ぶ。Phase 1.5 で Redis / PostgreSQL 永続化を検討。

---

## 7. 承認要否マトリクス

### 7.1 マトリクス表（v1 暫定）

| tool | 包絡線内 / 通常条件 | 包絡線外または特殊条件 | 承認要否 | タイムアウト | timeout デフォルト | 備考 |
|---|---|---|---|---|---|---|
| `set_perfusion_rate` | 0–7 vvd かつ ramp ≤ 0.5 vvd/30min | >7 vvd または ramp 超過 | 包絡線内: **不要** / 外: **要** | 10 min | `cancel` | 主レバー。L1 自律で可 |
| `set_agitation_rpm` | 30–150 rpm かつ ramp ≤ 20 rpm/5min | 外または急変 | 包絡線内: 不要 / 外: 要 | 10 min | `cancel` | 凝集体シア管理 |
| `set_gas_setpoint(DO)` | 5–50 % かつ ramp ≤ 5 %/5min | 外 | 包絡線内: 不要 / 外: 要 | 10 min | `cancel` | |
| `set_gas_setpoint(pH)` | 6.9–7.3 かつ ramp ≤ 0.1/5min | 外 | 包絡線内: 不要 / 外: 要 | 10 min | `cancel` | |
| `feed` | ボーラス量 ≤ 上限、グルコース/グルタミン各々包絡線内 | 量超過または未承認添加物 | 包絡線内: 不要 / 外: 要 | 10 min | `cancel` | |
| `exchange_media` | 交換率 ≤ 上限 | 全量交換等 | 通常: 不要 / 大容量: 要 | 10 min | `cancel` | |
| `take_sample` | サンプリング間隔 ≥ 最小 | 短過ぎる間隔 | 不要 | — | — | 読み取り系だが物理的干渉あり |
| `trigger_passage` | — | 常に重大アクション | **要** | 30 min | `cancel` | 解離継代。Y-27632 強制を検証 |
| `adjust_setpoint(temp)` | 36–38 ℃ | 外 | 包絡線内: 不要 / 外: 要 | 10 min | `cancel` | 通常は固定 |
| `contamination_suspected` 対応 | 安全系が即時停止 | ブレインからの CAPA 指示 | 要 | 60 min | `hold` | 安全系優先 |
| L2 BO 次 run 提案 | — | 常に要人間レビュー | **要** | 24 h | `reject` | run 間最適化 |

### 7.2 実装

```python
# src/auto_cell/hmi/approval_matrix.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml


@dataclass
class Decision:
    requires_approval: bool
    timeout_sec: float
    safe_default: str  # cancel / reject / hold


class ApprovalMatrix:
    def __init__(self, path: str):
        with open(path) as f:
            self._rules = yaml.safe_load(f)

    def decide(self, tool_name: str, params: dict[str, Any], run_context: dict[str, Any]) -> Decision:
        rule = self._rules.get(tool_name, {"requires_approval": True, "timeout_sec": 600, "safe_default": "cancel"})
        # 包絡線内判定は sanitizer と連携。ここでは簡易例。
        if tool_name == "set_perfusion_rate":
            vvd = params.get("vvd", 0.0)
            if 0.0 <= vvd <= 7.0:
                return Decision(False, 0.0, "cancel")
        return Decision(rule["requires_approval"], rule["timeout_sec"], rule["safe_default"])
```

### 7.3 YAML 例

```yaml
# config/approval_matrix.yaml
set_perfusion_rate:
  requires_approval: true
  timeout_sec: 600
  safe_default: cancel
  envelope:
    vvd: [0.0, 7.0]
    ramp_vvd_per_30min: [-0.5, 0.5]

set_agitation_rpm:
  requires_approval: true
  timeout_sec: 600
  safe_default: cancel
  envelope:
    rpm: [30, 150]
    ramp_rpm_per_5min: [-20, 20]

trigger_passage:
  requires_approval: true
  timeout_sec: 1800
  safe_default: cancel

l2_bo_proposal:
  requires_approval: true
  timeout_sec: 86400
  safe_default: reject
```

---

## 8. ダッシュボード骨格（API ファースト）

### 8.1 設計方針

- Phase 1 は **REST API + 最小 HTML**（または curl/script）。洗練 UI は Phase 1.5。
- ダッシュボード表示データは `event_store` から導出するビュー。`dashboard_service` は集計のみ。

### 8.2 エンドポイント

```python
# src/auto_cell/hmi/approval_api.py（追加）
from fastapi import Query
from datetime import datetime


@app.get("/hmi/runs/{run_id}/status")
async def run_status(run_id: str):
    """現在の CPP・phase・承認待ち件数を返す。"""
    svc, event_writer, _ = get_services()
    latest = _read_latest_telemetry(event_writer.base_dir, run_id)
    return {
        "run_id": run_id,
        "phase": latest.get("phase", "unknown"),
        "cpp": {
            "vcd": latest.get("vcd"),
            "viability": latest.get("viability"),
            "glucose": latest.get("glucose"),
            "lactate": latest.get("lactate"),
            "ph": latest.get("ph"),
            "do": latest.get("do_percent"),
            "aggregate_diameter_um": latest.get("aggregate_diameter_um"),
        },
        "pending_approvals": len(svc.list_pending()),
    }


@app.get("/hmi/runs/{run_id}/trend")
async def run_trend(
    run_id: str,
    channel: str = Query(...),
    start: datetime | None = None,
    end: datetime | None = None,
):
    """指定チャネルの時系列を返す。"""
    return _read_telemetry(event_writer.base_dir, run_id, channel, start, end)


@app.get("/hmi/runs/{run_id}/events")
async def run_events(run_id: str, limit: int = 100):
    """直近イベント一覧。"""
    return _read_events(event_writer.base_dir, run_id, limit)
```

### 8.3 最小 UI（オプション）

- `/hmi` に `text/html` でテーブル表示する軽量エンドポイントを用意。
- Phase 1.5 で React/Vue に置き換え。

---

## 9. EBR-like レポート：1 run = 1 report

### 9.1 導出方法

`event_store` の `run_id` 配下 JSONL を時系列で読み込み、以下を Markdown/PDF/JSON で出力する。

```python
# src/auto_cell/audit/ebr_report.py
from pathlib import Path
from typing import Any

from auto_cell.schemas.audit_events import EventType


def build_ebr(base_dir: Path, run_id: str) -> dict[str, Any]:
    events = _load_run_events(base_dir, run_id)
    report = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_events": len(events),
            "commands": len([e for e in events if e.header.event_type == EventType.COMMAND]),
            "tool_executions": len([e for e in events if e.header.event_type == EventType.TOOL_EXEC]),
            "approvals": len([e for e in events if e.header.event_type == EventType.APPROVAL]),
        },
        "timeline": [e.model_dump(mode="json") for e in events],
        "audit_chain_valid": len(AuditLog(base_dir).verify(run_id)) == 0,
    }
    return report
```

### 9.2 レポート API

```python
@app.get("/hmi/runs/{run_id}/ebr")
async def get_ebr(run_id: str):
    _, event_writer, audit_log = get_services()
    report = build_ebr(event_writer.base_dir, run_id)
    return report
```

---

## 10. テスト計画

### 10.1 承認フロー E2E テスト

```python
# tests/test_approval_flow.py
import pytest
from datetime import datetime, timezone

from auto_cell.hmi.approval_service import ApprovalService, ApprovalState
from auto_cell.audit.event_store import EventWriter
from auto_cell.audit.audit_log import AuditLog
from auto_cell.hmi.approval_matrix import ApprovalMatrix


@pytest.fixture
def services(tmp_path):
    ew = EventWriter(tmp_path / "events")
    al = AuditLog(tmp_path / "audit")
    matrix = ApprovalMatrix("config/approval_matrix.yaml")
    svc = ApprovalService(ew, al, matrix)
    return svc, ew, al


@pytest.mark.asyncio
async def test_request_approve_execute(services):
    svc, ew, al = services
    req = await svc.request(
        run_id="run_001",
        tool_name="set_perfusion_rate",
        params={"vvd": 8.5},
        requested_by="system",
        timeout_sec=600,
        safe_default="cancel",
        correlation_id="corr_1",
        reason="lactate high, need higher perfusion",
    )
    assert req.state == ApprovalState.REQUESTED

    approved = svc.approve(req.request_id, "user:tanaka", "confirmed by shift leader")
    assert approved.state == ApprovalState.APPROVED

    executed = svc.execute(req.request_id)
    assert executed.state == ApprovalState.EXECUTED

    # audit log 検証
    assert len(al.verify("run_001")) == 0


@pytest.mark.asyncio
async def test_timeout_cancels(services):
    svc, ew, al = services
    req = await svc.request(
        run_id="run_001",
        tool_name="trigger_passage",
        params={},
        requested_by="system",
        timeout_sec=0.1,
        safe_default="cancel",
        correlation_id="corr_2",
        reason="vcd target reached",
    )
    await asyncio.sleep(0.2)
    assert req.state == ApprovalState.CANCELLED
```

### 10.2 ALCOA-lite 監査テスト

```python
# tests/test_audit_log.py
import json

from auto_cell.audit.audit_log import AuditLog


def test_hash_chain_integrity(tmp_path):
    log = AuditLog(tmp_path)
    log.append("run_001", "system", "tool_executed", "set_perfusion_rate", {"vvd": 3.0}, "glucose low", "corr_1")
    log.append("run_001", "user:tanaka", "approval_approved", "set_perfusion_rate", {"vvd": 8.5}, "confirmed", "corr_1")
    assert log.verify("run_001") == []


def test_tamper_detection(tmp_path):
    log = AuditLog(tmp_path)
    log.append("run_001", "system", "tool_executed", "set_perfusion_rate", {"vvd": 3.0}, "glucose low", "corr_1")
    path = log._path("run_001")
    lines = path.read_text().splitlines()
    bad = json.loads(lines[0])
    bad["params"]["vvd"] = 99.0
    lines[0] = json.dumps(bad)
    path.write_text("\n".join(lines) + "\n")
    assert len(log.verify("run_001")) >= 1
```

### 10.3 tool_executor テスト

```python
# tests/test_tool_executor.py
import pytest

from auto_cell.audit.tool_executor import ToolExecutor, execution_context, ApprovalRequiredError


@pytest.mark.asyncio
async def test_envelope_auto_execute(services, tmp_path):
    svc, ew, al = services
    matrix = ApprovalMatrix("config/approval_matrix.yaml")
    async def set_perfusion_rate(vvd: float):
        return {"vvd": vvd}
    executor = ToolExecutor(ew, al, svc, matrix, {"set_perfusion_rate": set_perfusion_rate})

    with execution_context("run_001", "system", "corr_1", "glucose low"):
        result = await executor.execute("set_perfusion_rate", {"vvd": 3.0})
    assert result["vvd"] == 3.0
    assert len(al.verify("run_001")) == 0


@pytest.mark.asyncio
async def test_out_of_envelope_requires_approval(services, tmp_path):
    svc, ew, al = services
    matrix = ApprovalMatrix("config/approval_matrix.yaml")
    executor = ToolExecutor(ew, al, svc, matrix, {"set_perfusion_rate": lambda vvd: {"vvd": vvd}})

    with execution_context("run_001", "system", "corr_2", "lactate emergency"):
        with pytest.raises(ApprovalRequiredError):
            await executor.execute("set_perfusion_rate", {"vvd": 8.5})
```

### 10.4 網羅目標

| テスト | 確認事項 |
|---|---|
| 承認→実行 | `requested → approved → executed` |
| 拒否 | `requested → rejected → cancelled` |
| タイムアウト | 安全側デフォルトで `cancelled` / `hold` |
| 重複承認 | 終了状態への遷移を 409 で拒否 |
| ハッシュチェーン | 改ざん検知、空の run 検証 |
| ALCOA 完全性 | 全 tool 実行後に audit_log が 1 行以上増加 |
| 包絡線内外 | 包絡線内は自律実行、外は承認要求 |
| EBR 導出 | 1 run のイベント数・承認数がレポートに含まれる |

---

## 11. 依存関係

### 11.1 追加パッケージ

`pyproject.toml` に以下を追加する。

```toml
[project.dependencies]
"fastapi>=0.110",
"uvicorn[standard]>=0.29",
"python-multipart>=0.0.9",   # 将来的なフォーム認証用
"pyyaml>=6.0",               # 承認マトリクス YAML
"python-jose[cryptography]>=3.3",  # 軽量 JWT（認証 stub、必要なら）
```

### 11.2 既存依存との関係

- `physical-ai-core` の `DomainVertical` / tool 呼び出し機構が確定次第、`tool_executor` はそちらに委譲する。
- `paho-mqtt` は Sprint 6 の `gateway/mqtt_client.py` で追加済みを想定。承認 state topic は MQTT でも publish する。

---

## 12. リスクと対応

| # | リスク | 影響 | 対応 |
|---|---|---|---|
| R1 | 承認応答遅延 / 研究者不在 | タイムアウト直前に安全でない状態が続く | 安全側デフォルトを **cancel** とし、L1 は代替の包絡線内アクションを選択。`trigger_passage` など重大アクションは **hold** し手動対応を促す |
| R2 | 承認状態の in-memory 管理がプロセス再起動で失われる | 承認待ちアクションが消失 | 起動時 `cancel_all_pending(safe_default)` で安全側に倒す。Phase 1.5 で Redis/DB 永続化 |
| R3 | 状態管理の複雑性 | L1 実行判定バグ | 状態遷移を `ApprovalState` enum + 単方向遷移に制限。テストで全遷移を網羅 |
| R4 | audit_log と event_store の不整合 | ALCOA-lite 破綻 | `ToolExecutor` で dual-write。テストで件数一致を確認 |
| R5 | 承認要否マトリクスの運用誤設定 | 自動化過多または承認過多 | `config/approval_matrix.yaml` を研究者・PM 合意後 git 管理。レビュー基準に含める |
| R6 | ハッシュチェーンの計算コスト | 高頻度テレメトリ書き込み | テレメトリは event_store にのみ書き、audit_log には副作用・承認・コマンドのみを記録 |
| R7 | FastAPI サーバー停止時の HMI 不能 | 承認操作ができない | API サーバーは L1 と分離して独立起動。停止時はコマンドライン承認スクリプトで救済 |

---

## 13. Phase 2 GMP-ready 拡張（実装済み）

Sprint 7 の ALCOA-lite 骨格に対し、以下の GMP-ready 機能を Phase 2 で追加実装した。

| 機能 | 内容 | 主要ファイル |
|---|---|---|
| Identity / RBAC | bcrypt パスワード/PIN ハッシュ、JWT アクセス トークン、最小限のロール | `src/auto_cell/auth/` |
| 電子署名 | 承認/却下時に PIN と meaning-of-signature を要求 | `src/auto_cell/hmi/approval_service.py` |
| 職員独立性 | 承認者と要求者が同一ユーザーの場合は拒否 | `src/auto_cell/hmi/approval_service.py` |
| 承認永続化 | SQLite テーブルで承認要求を永続化し、再起動後も復元 | `src/auto_cell/hmi/approval_store.py` |
| 監査証跡レビュー | レビュー者・コメント・日時を audit_log に記録し EBR に含める | `src/auto_cell/audit/audit_log.py`, `ebr_report.py` |
| HMI ログイン | `/hmi/login` から JWT を取得し、ダッシュボードで承認操作を実施 | `src/auto_cell/hmi/templates/login.html`, `static/js/auth.js` |

これにより M05 は Phase 1 の「API + ALCOA-lite」から、Phase 2 の「認証・電子署名・承認永続化・レビュー記録」へ移行した。

## 14. 実装工数見積もり（週単位）

`05_implementation_plan_phase1.md` の Sprint 7（1 週間）をベースに、品質担保を含めた実工数を見積もる。

| 週 | タスク | 成果物 | 担当想定 |
|---|---|---|---|
| Week 7-1 | event_store / audit_log / tool_executor 骨格実装・単体テスト | `event_store.py`, `audit_log.py`, `tool_executor.py`, `test_audit_log.py` | 開発者 1 |
| Week 7-1（並行） | 承認状態機械・承認要否マトリクス実装 | `approval_service.py`, `approval_matrix.py`, `config/approval_matrix.yaml` | 開発者 2 |
| Week 7-2 | FastAPI 承認キュー + ダッシュボード API 実装 | `approval_api.py`, `dashboard_service.py`, `test_approval_flow.py` | 開発者 1 |
| Week 7-2（並行） | EBR レポート導出・MQTT state/approval topic 統合 | `ebr_report.py`, MQTT publisher hook, `test_dashboard_api.py` | 開発者 2 |
| Week 7-3 | L1 エンジン統合・HITL E2E テスト・レビュー | `scripts/run_closed_loop_sim.py` 統合、HITL レビュー pass | 全員 |

**合計: 2–2.5 週間**（Sprint 7 を 1 週間とする場合、並行 2 名で 1 週間完了も可能だが、レビュー・E2E 安定化を含めると 2 週間を確保することを推奨）。

---

## 15. 参照

- `docs/design/closed_loop_planning/05_implementation_plan_phase1.md`
- `docs/design/closed_loop_planning/06_critical_path_and_work_order.md`
- `docs/design/closed_loop_planning/03_swarm_findings_integration.md`
- `docs/design/closed_loop_planning/02_missing_assets_for_closed_loop.md`
- `docs/design/kg_to_auto_cell.md`
- `docs/design/adr/0001-control-architecture.md`
