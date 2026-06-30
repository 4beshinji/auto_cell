"""Recipe state machine wrapping ``transitions``."""

from __future__ import annotations

import logging

from transitions import Machine

from auto_cell.l1.recipe_loader import ConditionEvaluator
from auto_cell.l1.types import Condition, Context, Recipe, ToolCall

logger = logging.getLogger(__name__)


class RecipeStateMachine:
    """State machine driven by a Pydantic Recipe.

    The state machine is side-effect free with regard to the plant: entry/exit
    actions are collected as ``ToolCall`` objects and executed later by the
    cycle executor.
    """

    # ``transitions.Machine`` dynamically injects this attribute.
    state: str

    def __init__(self, recipe: Recipe, context: Context) -> None:
        self.recipe = recipe
        self.context = context
        self.evaluator = ConditionEvaluator(context)
        self.pending_entry_actions: list[ToolCall] = []
        self.pending_exit_actions: list[ToolCall] = []
        # Track when each state was entered so timeouts are evaluated relative to
        # the state entry moment, not absolute elapsed hours.
        self._state_entered_at: dict[str, float] = {}

        states = list(recipe.states.keys())
        self.machine = Machine(
            model=self,
            states=states,
            initial=recipe.initial_state,
            send_event=True,
            auto_transitions=False,
            model_attribute="state",
        )
        self._state_entered_at[recipe.initial_state] = 0.0

    def _evaluate_condition(self, condition: Condition | None, elapsed_hours: float) -> bool:
        if condition is None:
            return True
        self.context = self.context.model_copy(update={"elapsed_hours": elapsed_hours})
        self.evaluator.context = self.context
        return self.evaluator.evaluate(condition)

    def evaluate_transitions(self, elapsed_hours: float) -> list[str]:
        """Return target state IDs that are reachable from the current state.

        If the state defines an ``exit_condition``, it must be satisfied before
        any transition is considered.
        """
        state = self.recipe.get_state(self.state)
        if state.exit_condition is not None:
            if not self._evaluate_condition(state.exit_condition, elapsed_hours):
                return []
        targets = [
            tx.target
            for tx in state.transitions
            if self._evaluate_condition(tx.condition, elapsed_hours)
        ]
        if len(targets) > 1:
            logger.warning(
                "multiple transitions satisfied from state %r: %s; choosing %r",
                self.state,
                targets,
                targets[0],
            )
        return targets

    def apply_timeout(self, elapsed_hours: float) -> str | None:
        """Return the timeout target if the current state has expired."""
        state = self.recipe.get_state(self.state)
        entered_at = self._state_entered_at.get(self.state, elapsed_hours)
        elapsed_in_state = elapsed_hours - entered_at
        if state.timeout_hours is not None and elapsed_in_state >= state.timeout_hours:
            return state.on_timeout
        if state.timeout_minutes is not None and elapsed_in_state >= state.timeout_minutes / 60.0:
            return state.on_timeout
        return None

    def to_state(self, target: str, *, elapsed_hours: float | None = None) -> None:
        """Move to *target*, collecting exit/entry actions."""
        if elapsed_hours is not None:
            self.context = self.context.model_copy(update={"elapsed_hours": elapsed_hours})
            self.evaluator.context = self.context
        old_state = self.recipe.get_state(self.state)
        self.pending_exit_actions.extend(old_state.on_exit)
        self.machine.set_state(target)
        new_state = self.recipe.get_state(target)
        self.pending_entry_actions.extend(new_state.entry_actions)
        self._state_entered_at[target] = elapsed_hours if elapsed_hours is not None else 0.0
        self.context = self.context.model_copy(update={"state_id": target})
        self.evaluator.context = self.context
