"""Deterministic rule engine for L1."""

from __future__ import annotations

from auto_cell.l1.recipe_loader import ConditionEvaluator
from auto_cell.l1.types import ActionCandidate, Context, Recipe, Rule
from auto_cell.plugins.cell_culture.environment import CellCultureEnv


_PRIORITY_ORDER = ("P0", "P1", "P2", "P3")


class RuleEngine:
    """Evaluate a list of deterministic rules against the current culture env."""

    def __init__(self, rules: list[Rule], recipe: Recipe | None = None) -> None:
        self.rules = rules
        self.recipe = recipe
        self.last_fired_at: dict[str, float] = {}
        self._sensor_since: dict[str, float] = {}

    def evaluate(
        self,
        env: CellCultureEnv,
        events: list[str],
        elapsed_hours: float,
        approvals: dict[str, str] | None = None,
    ) -> list[ActionCandidate]:
        context = Context(
            recipe=self.recipe,
            env=env,
            elapsed_hours=elapsed_hours,
            state_id="",
            event_log=events,
            approvals=approvals or {},
        )
        # Preserve continuous-sensor state across evaluate() calls so that
        # ``SensorCondition.for_minutes`` can be evaluated correctly.
        context._sensor_since = self._sensor_since.copy()
        evaluator = ConditionEvaluator(context)
        candidates: list[ActionCandidate] = []

        for rule in self.rules:
            last = self.last_fired_at.get(rule.id)
            if last is not None and (elapsed_hours - last) < (rule.cooldown_minutes / 60.0):
                continue

            if evaluator.evaluate(rule.when):
                for action in rule.actions:
                    candidates.append(
                        ActionCandidate(
                            source=f"rule:{rule.id}",
                            priority=rule.priority,
                            action=action,
                            reason=f"{rule.id} fired",
                        )
                    )
                self.last_fired_at[rule.id] = elapsed_hours

        self._sensor_since = context._sensor_since
        candidates.sort(key=lambda c: _PRIORITY_ORDER.index(c.priority))
        return candidates
