"""L1 deterministic recipe/rule engine Pydantic models."""

from __future__ import annotations

from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field, PrivateAttr, model_validator


class ScalarValue(BaseModel):
    value: float | int | str | bool
    unit: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_numeric_strings(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("value"), str):
            raw = data["value"]
            try:
                data = dict(data)
                data["value"] = int(raw)
                return data
            except ValueError:
                pass
            try:
                data = dict(data)
                data["value"] = float(raw)
                return data
            except ValueError:
                pass
        return data


class ValueRef(BaseModel):
    ref: str


class SensorCondition(BaseModel):
    sensor: str
    op: str = "ge"
    value: Any = None
    min_value: Any = None
    max_value: Any = None
    for_minutes: float = 0.0

    @model_validator(mode="before")
    @classmethod
    def _resolve_op_aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        ops = ("eq", "ne", "gt", "ge", "lt", "le", "in_range")
        # Already normalized
        if data.get("op") in ops:
            return data
        for op in ops:
            if op in data:
                data = dict(data)
                data["op"] = op
                data["value"] = data.pop(op)
                return data
            ref_key = f"{op}_ref"
            if ref_key in data:
                data = dict(data)
                data["op"] = op
                data["value"] = data.pop(ref_key)
                return data
        return data


class EventCondition(BaseModel):
    event: str
    op: Literal["occurred", "not_occurred", "suppressed"] = "occurred"
    within_minutes: float | None = None


class ApprovalCondition(BaseModel):
    approval: str
    state: Literal["approved", "rejected", "pending", "timeout"]


class LogicalCondition(BaseModel):
    and_: Optional[List["Condition"]] = Field(None, alias="and")
    or_: Optional[List["Condition"]] = Field(None, alias="or")
    not_: Optional["Condition"] = Field(None, alias="not")


Condition = Union[SensorCondition, EventCondition, ApprovalCondition, LogicalCondition]


class ToolCall(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


class ScheduledAction(BaseModel):
    every_hours: float | None = None
    every_minutes: float | None = None
    at_hours: list[float] | None = None
    action: ToolCall


class Transition(BaseModel):
    target: str
    condition: Condition | None = None
    timeout_hours: float | None = None
    timeout_minutes: float | None = None
    on_timeout: str | None = None


class State(BaseModel):
    id: str
    entry_actions: list[ToolCall] = Field(default_factory=list)
    scheduled_actions: list[ScheduledAction] = Field(default_factory=list)
    exit_condition: Condition | None = None
    transitions: list[Transition] = Field(default_factory=list)
    timeout_hours: float | None = None
    timeout_minutes: float | None = None
    on_timeout: str | None = None
    on_exit: list[ToolCall] = Field(default_factory=list)


class Recipe(BaseModel):
    id: str
    version: str
    title: str
    culture_unit_id: str
    initial_state: str
    setpoints: dict[str, ScalarValue] = Field(default_factory=dict)
    variables: dict[str, ScalarValue] = Field(default_factory=dict)
    states: dict[str, State]

    def get_state(self, state_id: str) -> State:
        if state_id not in self.states:
            raise KeyError(f"state {state_id!r} not in recipe")
        return self.states[state_id]


class ActionCandidate(BaseModel):
    source: str
    priority: Literal["P0", "P1", "P2", "P3"]
    action: ToolCall
    reason: str


class Rule(BaseModel):
    id: str
    priority: Literal["P0", "P1", "P2", "P3"]
    when: Condition
    actions: list[ToolCall]
    cooldown_minutes: float = 0.0


class Context(BaseModel):
    recipe: Recipe | None = None
    env: Any = None
    elapsed_hours: float = 0.0
    state_id: str = ""
    event_log: list[str] = Field(default_factory=list)
    approvals: dict[str, str] = Field(default_factory=dict)

    # Tracks when each sensor condition first became continuously true,
    # so ``SensorCondition.for_minutes`` can be evaluated against elapsed
    # simulation hours. Keys are sensor names; values are elapsed_hours.
    _sensor_since: dict[str, float] = PrivateAttr(default_factory=dict)

    def resolve(self, ref: str) -> Any:
        if ref.startswith("variables."):
            key = ref.split(".")[1]
            if self.recipe is None:
                raise ValueError(f"unresolvable ref (no recipe): {ref}")
            return self.recipe.variables[key].value
        if ref.startswith("setpoints."):
            key = ref.split(".")[1]
            if self.recipe is None:
                raise ValueError(f"unresolvable ref (no recipe): {ref}")
            return self.recipe.setpoints[key].value
        if ref.startswith("cycle.env."):
            key = ref.split(".")[2]
            if self.env is None:
                raise ValueError(f"unresolvable ref (no env): {ref}")
            return getattr(self.env, key)
        if ref == "cycle.elapsed_hours":
            return self.elapsed_hours
        if ref == "cycle.state_id":
            return self.state_id
        raise ValueError(f"unresolvable ref: {ref}")


class CycleResult(BaseModel):
    cycle: int
    elapsed_hours: float
    state_id: str
    sensor_snapshot: Any
    events: list[str]
    candidates: list[ActionCandidate]
    executed: list[ToolCall]
    rejected: list[ToolCall]
    approval_requested: list[ToolCall]


LogicalCondition.model_rebuild()
