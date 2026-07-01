"""Approval request persistence backends."""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from auto_cell.hmi.approval_models import ApprovalRequest


class ApprovalStore(ABC):
    """Abstract persistence layer for approval requests."""

    @abstractmethod
    def get(self, request_id: str) -> ApprovalRequest | None:
        """Return the request or None."""

    @abstractmethod
    def put(self, request: ApprovalRequest) -> None:
        """Insert or replace a request."""

    @abstractmethod
    def delete(self, request_id: str) -> None:
        """Remove a request from the store."""

    @abstractmethod
    def list_pending(self) -> list[ApprovalRequest]:
        """Return all requests in REQUESTED state."""

    @abstractmethod
    def list_all(self) -> list[ApprovalRequest]:
        """Return all stored requests."""

    def find_approved(
        self,
        run_id: str,
        tool_name: str,
        params: dict[str, Any],
        correlation_id: str,
    ) -> ApprovalRequest | None:
        """Find an existing approved request matching the action."""
        for req in self.list_all():
            if (
                req.run_id == run_id
                and req.tool_name == tool_name
                and req.params == params
                and req.correlation_id == correlation_id
                and req.state.value == "approved"
            ):
                return req
        return None


class InMemoryApprovalStore(ApprovalStore):
    """In-memory store for tests and backward compatibility."""

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}

    def get(self, request_id: str) -> ApprovalRequest | None:
        return self._requests.get(request_id)

    def put(self, request: ApprovalRequest) -> None:
        self._requests[request.request_id] = request

    def delete(self, request_id: str) -> None:
        self._requests.pop(request_id, None)

    def list_pending(self) -> list[ApprovalRequest]:
        return [r for r in self._requests.values() if r.state.value == "requested"]

    def list_all(self) -> list[ApprovalRequest]:
        return list(self._requests.values())


class SqliteApprovalStore(ApprovalStore):
    """SQLite-backed persistent approval store for GMP Phase 2."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS approval_requests (
                    request_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    state TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_approval_run_state ON approval_requests(run_id, state)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_approval_tool ON approval_requests(run_id, tool_name, state)"
            )
            conn.commit()

    @staticmethod
    def _serialize(request: ApprovalRequest) -> str:
        return request.model_dump_json()

    @staticmethod
    def _deserialize(text: str) -> ApprovalRequest:
        return ApprovalRequest.model_validate_json(text)

    def get(self, request_id: str) -> ApprovalRequest | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM approval_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if row is None:
                return None
            return self._deserialize(row[0])

    def put(self, request: ApprovalRequest) -> None:
        payload = self._serialize(request)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO approval_requests (request_id, run_id, tool_name, state, correlation_id, payload, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(request_id) DO UPDATE SET
                    run_id=excluded.run_id,
                    tool_name=excluded.tool_name,
                    state=excluded.state,
                    correlation_id=excluded.correlation_id,
                    payload=excluded.payload,
                    updated_at=excluded.updated_at
                """,
                (
                    request.request_id,
                    request.run_id,
                    request.tool_name,
                    request.state.value,
                    request.correlation_id,
                    payload,
                    request.requested_at.isoformat(),
                ),
            )
            conn.commit()

    def delete(self, request_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM approval_requests WHERE request_id = ?", (request_id,)
            )
            conn.commit()

    def list_pending(self) -> list[ApprovalRequest]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM approval_requests WHERE state = 'requested' ORDER BY updated_at"
            ).fetchall()
            return [self._deserialize(row[0]) for row in rows]

    def list_all(self) -> list[ApprovalRequest]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM approval_requests ORDER BY updated_at"
            ).fetchall()
            return [self._deserialize(row[0]) for row in rows]

    def find_approved(
        self,
        run_id: str,
        tool_name: str,
        params: dict[str, Any],
        correlation_id: str,
    ) -> ApprovalRequest | None:
        # Use indexed filters to avoid deserializing every row.
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload FROM approval_requests
                WHERE run_id = ? AND tool_name = ? AND state = 'approved' AND correlation_id = ?
                """,
                (run_id, tool_name, correlation_id),
            ).fetchall()
            for row in rows:
                req = self._deserialize(row[0])
                if req.params == params:
                    return req
        return None
