"""Append-only audit log with SHA-256 hash chain."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from auto_cell._utils import validate_run_id


class AuditRecord(BaseModel):
    seq: int
    run_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str
    action: str
    target: str
    params: dict[str, Any]
    reason: str
    correlation_id: str | None
    prev_hash: str
    hash: str


class AuditLog:
    GENESIS_HASH: str = "0" * 64

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self._seq: dict[str, int] = {}
        self._last_hash: dict[str, str] = {}

    def _path(self, run_id: str) -> Path:
        validate_run_id(run_id)
        dir_ = self.base_dir / run_id
        dir_.mkdir(parents=True, exist_ok=True)
        path = dir_ / "audit.jsonl"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                last_line = ""
                for line in f:
                    line = line.strip()
                    if line:
                        last_line = line
                if last_line:
                    record = json.loads(last_line)
                    self._seq[run_id] = record["seq"]
                    self._last_hash[run_id] = record["hash"]
                    return path
        self._seq[run_id] = 0
        self._last_hash[run_id] = self.GENESIS_HASH
        return path

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
        path = self._path(run_id)
        seq = self._seq.get(run_id, 0) + 1
        prev_hash = self._last_hash.get(run_id, self.GENESIS_HASH)
        record = AuditRecord(
            seq=seq,
            run_id=run_id,
            actor=actor,
            action=action,
            target=target,
            params=params,
            reason=reason,
            correlation_id=correlation_id,
            prev_hash=prev_hash,
            hash="",
        )
        body = record.model_dump(mode="json", exclude={"hash"})
        h = self._compute_hash(body)
        record.hash = h
        line = record.model_dump_json(ensure_ascii=False)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            os.fsync(f.fileno())
        self._seq[run_id] = seq
        self._last_hash[run_id] = h
        return record

    def load(self, run_id: str) -> list[AuditRecord]:
        """Load all audit records for a run."""
        path = self._path(run_id)
        records: list[AuditRecord] = []
        if not path.exists():
            return records
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                records.append(AuditRecord.model_validate_json(line))
        return records

    def review(self, run_id: str, reviewer: str, comments: str) -> AuditRecord:
        """Record an audit-trail review event (ALCOA+ review workflow)."""
        return self.append(
            run_id=run_id,
            actor=reviewer,
            action="audit_trail_reviewed",
            target="audit_log",
            params={},
            reason=comments,
        )

    def verify(self, run_id: str) -> list[str]:
        """Verify the chain. Returns list of broken seq messages. Empty list = OK."""
        broken: list[str] = []
        path = self._path(run_id)
        if not path.exists():
            return broken
        prev_hash = self.GENESIS_HASH
        expected_seq = 1
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record["seq"] != expected_seq:
                    broken.append(f"seq {record['seq']}: expected {expected_seq}")
                expected_seq += 1
                if record["prev_hash"] != prev_hash:
                    broken.append(f"seq {record['seq']}: prev_hash mismatch")
                body = {k: v for k, v in record.items() if k != "hash"}
                if self._compute_hash(body) != record["hash"]:
                    broken.append(f"seq {record['seq']}: hash mismatch")
                prev_hash = record["hash"]
        return broken
