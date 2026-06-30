"""Shared utilities for auto_cell."""

from __future__ import annotations

import re

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def validate_run_id(value: str) -> str:
    if not isinstance(value, str) or not _RUN_ID_RE.match(value):
        raise ValueError(f"invalid run_id/request_id: {value!r}")
    return value
