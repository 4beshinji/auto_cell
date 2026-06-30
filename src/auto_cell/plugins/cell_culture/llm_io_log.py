"""Schema and helper for logging L3 LLM inputs/outputs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from auto_cell.l3_orchestrator import L3Recommendation, L3TriggerType


class LlmIoLog(BaseModel):
    """Immutable record of one L3 LLM invocation."""

    call_id: str
    trigger_type: L3TriggerType
    prompt_version: str
    prompt_hash: str
    model: str
    request_payload: dict[str, Any]
    response_payload: dict[str, Any]
    parsed_recommendation: L3Recommendation
    latency_ms: int
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def append_to(self, log_dir: Path) -> Path:
        log_dir.mkdir(parents=True, exist_ok=True)
        # Sanitize ISO timestamp for filesystem names.
        ts = self.timestamp.replace(":", "-")
        path = log_dir / f"{ts}_{self.call_id}.json"
        path.write_text(
            self.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path
