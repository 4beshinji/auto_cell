"""cell_culture domain plugin (iPSC suspension bioreactor) — Phase 1."""

from datetime import datetime, timezone
from typing import Any, Callable

from physical_ai_core.brain.plugin_base import BrainContext, ChannelConfig, DomainVertical
from pydantic import BaseModel

from auto_cell.plugins.cell_culture.channels import channel_config as _channel_config
from auto_cell.plugins.cell_culture.channels import route_channel as _route_channel
from auto_cell.plugins.cell_culture.aggregate_imaging_service import (
    AggregateImagingService,
)
from auto_cell.plugins.cell_culture.environment import CellCultureEnv
from auto_cell.plugins.cell_culture.events import (
    CultureEvent,
    detect_events as _detect_events,
    event_descriptions as _event_descriptions,
    suppression_defaults as _suppression_defaults,
)
from auto_cell.plugins.cell_culture.prompt import (
    build_culture_unit_summary as _build_summary,
    system_prompt_section as _system_prompt,
)
from auto_cell.plugins.cell_culture.sanitizer import validate_tool_call as _validate_tool_call
from auto_cell.plugins.cell_culture.tools import (
    ToolResult,
    invoke_tool as _invoke_tool,
    tool_handlers as _tool_handlers,
    tool_schemas as _tool_schemas,
)

__all__ = [
    "AggregateImagingService",
    "CellCulturePlugin",
    "CellCultureEnv",
    "CultureEvent",
    "ToolResult",
    "plugin_class",
]


class CellCulturePlugin(DomainVertical):
    """physical-ai-core DomainVertical implementation for iPSC suspension culture."""

    def __init__(self):
        self._ctx: BrainContext | None = None

    def on_init(self, ctx: BrainContext) -> None:
        self._ctx = ctx

    @property
    def domain_id(self) -> str:
        return "cell_culture"

    @property
    def display_name(self) -> str:
        return "iPSC 浮遊/凝集体培養"

    def environment_model(self) -> type[CellCultureEnv]:
        return CellCultureEnv

    def culture_unit_field_name(self) -> str:
        return "cell_culture"

    def channel_config(self) -> dict[str, ChannelConfig]:
        return {
            ch.channel_id: ChannelConfig(
                channel_type=ch.kind,
                half_life=ch.cadence_s or 120.0,
                trend_threshold=ch.deadband or 1.0,
            )
            for ch in _channel_config()
        }

    def route_channel(self, env: BaseModel, channel: str, value: float, timestamp: float) -> bool:
        update = _route_channel(channel, value)
        if update is None:
            return False
        for key, val in update.items():
            setattr(env, key, val)
        return True

    def detect_events(self, culture_unit_id: str, culture_unit: Any, now: float) -> list:
        env = getattr(culture_unit.domain_envs, self.culture_unit_field_name(), None)
        if env is None:
            return []
        return _detect_events(env, datetime.fromtimestamp(now, tz=timezone.utc))

    def event_descriptions(self) -> dict[str, Callable[[dict], str]]:
        descriptions = _event_descriptions()
        return {k: lambda data, msg=msg: msg for k, msg in descriptions.items()}

    def suppression_defaults(self) -> dict[str, float]:
        # ``_suppression_defaults()`` already returns hours, matching
        # ``EventDispatcher`` expectations.
        return {k: float(v) for k, v in _suppression_defaults().items()}

    def tool_schemas(self) -> list[dict]:
        return [
            {"name": name, **schema}
            for name, schema in _tool_schemas().items()
        ]

    def tool_handlers(self, ctx: BrainContext) -> dict[str, Callable]:
        return {
            name: lambda args, h=handler: h(args)
            for name, handler in _tool_handlers().items()
        }

    def query_tool_names(self) -> set:
        return {"take_sample"}

    def validate_tool_call(self, tool_name: str, args: dict[str, Any]) -> tuple[bool, str]:
        if self._ctx is None or getattr(self._ctx, "world_model", None) is None:
            return False, "no world model"

        envs: list[CellCultureEnv] = []
        for cu in self._ctx.world_model.culture_units.values():
            domain_envs = cu.domain_envs
            env = getattr(domain_envs, "cell_culture", None)
            if env is None and hasattr(domain_envs, "get"):
                env = domain_envs.get("cell_culture")
            if env is not None:
                envs.append(env)

        if len(envs) > 1:
            return False, "multiple culture units"
        if len(envs) == 0:
            return False, "no cell_culture env available"

        env = envs[0]
        if not isinstance(env, CellCultureEnv):
            return False, "no cell_culture env available"

        result, reason = _validate_tool_call(env, tool_name, args)
        if result == "accepted":
            return True, ""
        return False, reason

    def system_prompt_section(self) -> str:
        return _system_prompt()

    def build_culture_unit_summary(
        self,
        culture_unit_id: str,
        culture_unit: Any,
        get_trend: Callable,
    ) -> str | None:
        env = getattr(culture_unit.domain_envs, self.culture_unit_field_name(), None)
        if env is None:
            return None
        return _build_summary(env)


plugin_class = CellCulturePlugin
