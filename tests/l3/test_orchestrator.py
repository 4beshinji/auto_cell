"""Tests for L3 LLM orchestrator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from auto_cell.l3_orchestrator import (
    L3Recommendation,
    L3Trigger,
    L3TriggerType,
    LlmOrchestrator,
)


@pytest.fixture
def orchestrator(tmp_path: Path) -> LlmOrchestrator:
    return LlmOrchestrator(
        model="gpt-4o-mini",
        prompt_version="v1",
        log_dir=tmp_path,
        allowed_tools=["get_culture_unit_status"],
    )


@pytest.mark.asyncio
async def test_prompt_hash_and_logging(orchestrator: LlmOrchestrator, tmp_path: Path):
    trigger = L3Trigger(
        trigger_type=L3TriggerType.RESEARCHER_DIALOGUE,
        culture_unit_id="cu-01",
        context={
            "culture_unit_id": "cu-01",
            "phase": "perfusion_ramp",
            "recent_events": ["glucose_low"],
            "state_summary": {"vcd": "1.0e6 cells/mL", "glucose": "1.5 mM"},
        },
    )

    fake_message = AsyncMock()
    fake_message.content = "test recommendation"
    fake_choice = AsyncMock()
    fake_choice.message = fake_message
    fake_response = AsyncMock()
    fake_response.choices = [fake_choice]
    fake_response.model_dump.return_value = {
        "choices": [{"message": {"content": "test recommendation"}}]
    }
    fake_response.model_dump_async = None

    with patch(
        "openai.chat.completions.create", new=AsyncMock(return_value=fake_response)
    ):
        rec = await orchestrator.handle(trigger)

    assert rec.requires_human_confirmation is True
    logs = list(tmp_path.glob("*.json"))
    assert len(logs) == 1
    log_text = logs[0].read_text(encoding="utf-8")
    assert orchestrator.system_hash in log_text


def test_critical_tool_guard_raises(orchestrator: LlmOrchestrator):
    rec = L3Recommendation(
        recommendation="",
        reasoning="",
        suggested_tool_calls=[{"name": "emergency_stop"}],
        confidence=0.5,
    )
    with pytest.raises(RuntimeError):
        orchestrator._enforce_guards(rec)


def test_unallowed_tool_guard_raises(orchestrator: LlmOrchestrator):
    rec = L3Recommendation(
        recommendation="",
        reasoning="",
        suggested_tool_calls=[{"name": "set_perfusion_rate"}],
        confidence=0.5,
    )
    with pytest.raises(RuntimeError):
        orchestrator._enforce_guards(rec)


def test_allowed_tool_guard_passes(orchestrator: LlmOrchestrator):
    rec = L3Recommendation(
        recommendation="",
        reasoning="",
        suggested_tool_calls=[{"name": "get_culture_unit_status"}],
        confidence=0.5,
        requires_human_confirmation=False,
    )
    orchestrator._enforce_guards(rec)
    assert rec.requires_human_confirmation is True
