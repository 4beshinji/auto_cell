"""L3 event-driven LLM orchestrator (advisory only, non-critical)."""

from __future__ import annotations

import hashlib
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class L3TriggerType(str, Enum):
    """L3 invocation trigger types. L3 is intentionally non-resident."""

    APPROVAL_MEDIATION = "approval_mediation"
    AMBIGUOUS_PERCEPTION = "ambiguous_perception"
    NOVEL_EXCEPTION = "novel_exception"
    RESEARCHER_DIALOGUE = "researcher_dialogue"


class L3Trigger(BaseModel):
    """Trigger payload for L3."""

    trigger_type: L3TriggerType
    culture_unit_id: str
    context: dict[str, Any] = Field(default_factory=dict)


class L3Recommendation(BaseModel):
    """L3 advice. Never acts directly; L1/approval workflow makes final decisions."""

    recommendation: str
    reasoning: str
    suggested_tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    requires_human_confirmation: bool = True


class PromptRegistry:
    """Load and version Jinja2 prompts for L3."""

    def __init__(self, version: str = "v1"):
        self.base = Path(__file__).parent / "plugins" / "cell_culture" / "prompts" / version
        self.version = version

    def load(self, name: str) -> str:
        return (self.base / name).read_text(encoding="utf-8")

    def hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class LlmOrchestrator:
    """Thin L3 LLM orchestrator for advisory, non-critical use cases only."""

    CRITICAL_TOOLS = {
        "set_safety_interlock",
        "disable_sterility_barrier",
        "emergency_stop",
    }

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        prompt_version: str = "v1",
        log_dir: Path | None = None,
        allowed_tools: list[str] | None = None,
    ):
        self.model = model
        self.registry = PromptRegistry(version=prompt_version)
        self.system_prompt = self.registry.load("system.jinja")
        self.system_hash = self.registry.hash(self.system_prompt)
        self.log_dir = log_dir or Path("logs/llm_io")
        self.allowed_tools = set(allowed_tools or [])

    async def handle(self, trigger: L3Trigger) -> L3Recommendation:
        user_msg = self._render_summary(trigger)
        request_payload = {
            "model": self.model,
            "temperature": 0.0,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_msg},
            ],
        }

        start = time.monotonic()
        # Delayed import to avoid circular dependency with llm_io_log.
        import openai

        response = await openai.chat.completions.create(**request_payload)  # type: ignore
        latency_ms = int((time.monotonic() - start) * 1000)

        recommendation = self._parse_response(response)
        self._enforce_guards(recommendation)

        # Delayed import to avoid circular dependency.
        from auto_cell.plugins.cell_culture.llm_io_log import LlmIoLog

        raw_response = response.model_dump(mode="json")
        if hasattr(raw_response, "__await__"):
            raw_response = await raw_response

        log = LlmIoLog(
            call_id=str(uuid.uuid4()),
            trigger_type=trigger.trigger_type,
            prompt_version=self.registry.version,
            prompt_hash=self.system_hash,
            model=self.model,
            request_payload=request_payload,
            response_payload=raw_response,
            parsed_recommendation=recommendation,
            latency_ms=latency_ms,
        )
        log.append_to(self.log_dir)
        return recommendation

    def _enforce_guards(self, rec: L3Recommendation) -> None:
        for tc in rec.suggested_tool_calls:
            name = tc.get("name")
            if name in self.CRITICAL_TOOLS:
                raise RuntimeError(
                    f"L3 must not suggest critical tool {name}"
                )
            if self.allowed_tools and name not in self.allowed_tools:
                raise RuntimeError(f"L3 must not suggest unallowed tool {name}")
        # L3 output always requires human confirmation.
        rec.requires_human_confirmation = True

    def _render_summary(self, trigger: L3Trigger) -> str:
        from jinja2 import Template

        tpl = self.registry.load("summary.jinja")
        return Template(tpl).render(**trigger.context)

    def _parse_response(self, response: Any) -> L3Recommendation:
        msg = response.choices[0].message
        return L3Recommendation(
            recommendation=msg.content or "",
            reasoning="Parsed from LLM response",
            suggested_tool_calls=[],
            confidence=0.7,
            requires_human_confirmation=True,
        )
