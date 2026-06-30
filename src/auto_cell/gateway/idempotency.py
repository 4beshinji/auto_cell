"""Request-id based duplicate execution prevention."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class IdempotencyRecord:
    request_id: str
    status: str
    result: dict[str, Any] | None = None
    expires_at: float = 0.0


class IdempotencyStore:
    """In-memory request_id deduplication store with TTL."""

    def __init__(self, ttl_seconds: float = 86400) -> None:
        self.ttl_seconds = ttl_seconds
        self._records: dict[str, IdempotencyRecord] = {}
        self._lock = threading.Lock()

    def _now(self) -> float:
        return time.monotonic()

    def is_known(self, request_id: str) -> bool:
        with self._lock:
            rec = self._records.get(request_id)
            if rec is None:
                return False
            if rec.expires_at < self._now():
                del self._records[request_id]
                return False
            return True

    def get(self, request_id: str) -> IdempotencyRecord | None:
        with self._lock:
            rec = self._records.get(request_id)
            if rec is None:
                return None
            if rec.expires_at < self._now():
                del self._records[request_id]
                return None
            return rec

    def save(
        self,
        request_id: str,
        status: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            self._records[request_id] = IdempotencyRecord(
                request_id=request_id,
                status=status,
                result=result,
                expires_at=self._now() + self.ttl_seconds,
            )

    def cleanup(self) -> None:
        with self._lock:
            now = self._now()
            expired = [rid for rid, rec in self._records.items() if rec.expires_at < now]
            for rid in expired:
                del self._records[rid]
