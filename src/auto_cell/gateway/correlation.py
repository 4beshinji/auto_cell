"""correlation_id / request_id generators."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def generate_correlation_id() -> str:
    """Cross-cutting ID linking cmd/ack/approval/event_store."""
    return f"c_{uuid.uuid4().hex}"


def generate_request_id() -> str:
    """Idempotency key for a single command or approval request."""
    return f"req_{uuid.uuid4().hex}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
