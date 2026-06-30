"""YAML/JSON recipe and rule loading plus condition evaluation."""

from __future__ import annotations

import json
import operator
from pathlib import Path
from typing import Any

import yaml

from auto_cell.l1.types import (
    ApprovalCondition,
    Condition,
    Context,
    EventCondition,
    LogicalCondition,
    Recipe,
    Rule,
    SensorCondition,
)


_COMPARATORS: dict[str, Any] = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gt": operator.gt,
    "ge": operator.ge,
    "lt": operator.lt,
    "le": operator.le,
}


def load_recipe(path: str | Path) -> Recipe:
    p = Path(path)
    raw = _load_file(p)
    if "recipe" in raw:
        raw = raw["recipe"]
    # Resolve state IDs inside each state dict if missing.
    if "states" in raw and isinstance(raw["states"], dict):
        for state_id, state_data in raw["states"].items():
            if isinstance(state_data, dict) and "id" not in state_data:
                state_data["id"] = state_id
    return Recipe.model_validate(raw)


def load_rules(path: str | Path) -> list[Rule]:
    p = Path(path)
    raw = _load_file(p)
    if "rules" in raw:
        raw = raw["rules"]
    return [Rule.model_validate(item) for item in raw]


def _load_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        if path.suffix in {".yaml", ".yml"}:
            return yaml.safe_load(fh)
        if path.suffix == ".json":
            return json.load(fh)
        # Best effort YAML (YAML is a superset of JSON).
        return yaml.safe_load(fh)


class ConditionEvaluator:
    """Evaluate DSL Condition objects against a Context."""

    def __init__(self, context: Context) -> None:
        self.context = context

    def evaluate(self, condition: Condition) -> bool:
        if isinstance(condition, LogicalCondition):
            return self._eval_logical(condition)
        if isinstance(condition, SensorCondition):
            return self._eval_sensor(condition)
        if isinstance(condition, EventCondition):
            return self._eval_event(condition)
        if isinstance(condition, ApprovalCondition):
            return self._eval_approval(condition)
        raise TypeError(f"unsupported condition type: {type(condition)}")

    def _resolve_value(self, value: Any) -> Any:
        if isinstance(value, str):
            try:
                return self.context.resolve(value)
            except ValueError:
                return value
        return value

    def _read_sensor(self, sensor: str) -> Any:
        if sensor == "cycle_elapsed_hours" or sensor == "cycle.elapsed_hours":
            return self.context.elapsed_hours
        if sensor == "cycle.state_id":
            return self.context.state_id
        if sensor.startswith("cycle.env."):
            field = sensor.split(".")[2]
            if self.context.env is None:
                raise ValueError(f"cannot read {sensor}: no env in context")
            return getattr(self.context.env, field)
        if self.context.env is None:
            raise ValueError(f"cannot read sensor {sensor}: no env in context")
        return getattr(self.context.env, sensor)

    def _eval_sensor(self, condition: SensorCondition) -> bool:
        actual = self._read_sensor(condition.sensor)
        op = condition.op
        if op == "in_range":
            low = self._resolve_value(condition.min_value)
            high = self._resolve_value(condition.max_value)
            if low is None or high is None:
                raise ValueError("in_range requires min_value and max_value")
            currently_true = low <= actual <= high
        else:
            cmp = _COMPARATORS.get(op)
            if cmp is None:
                raise ValueError(f"unsupported sensor op: {op}")
            expected = self._resolve_value(condition.value)
            currently_true = bool(cmp(actual, expected))

        elapsed_hours = self.context.elapsed_hours
        sensor_since = self.context._sensor_since

        if currently_true:
            if condition.sensor not in sensor_since:
                sensor_since[condition.sensor] = elapsed_hours
        else:
            sensor_since.pop(condition.sensor, None)

        if condition.for_minutes <= 0.0:
            return currently_true

        since = sensor_since.get(condition.sensor)
        if since is None:
            return False
        return elapsed_hours - since >= (condition.for_minutes / 60.0)

    def _eval_event(self, condition: EventCondition) -> bool:
        occurred = condition.event in self.context.event_log
        if condition.op == "occurred":
            return occurred
        if condition.op == "not_occurred":
            return not occurred
        if condition.op == "suppressed":
            return not occurred
        raise ValueError(f"unsupported event op: {condition.op}")

    def _eval_approval(self, condition: ApprovalCondition) -> bool:
        return self.context.approvals.get(condition.approval) == condition.state

    def _eval_logical(self, condition: LogicalCondition) -> bool:
        if condition.and_:
            return all(self.evaluate(c) for c in condition.and_)
        if condition.or_:
            return any(self.evaluate(c) for c in condition.or_)
        if condition.not_:
            return not self.evaluate(condition.not_)
        return True
