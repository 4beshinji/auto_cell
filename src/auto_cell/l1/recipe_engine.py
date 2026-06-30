"""L1 recipe engine: integrates state machine, rules, events, and planning."""

from __future__ import annotations

from auto_cell.l1.action_planner import ActionPlanner
from auto_cell.l1.event_dispatcher import EventDispatcher
from auto_cell.l1.recipe_loader import load_recipe, load_rules
from auto_cell.l1.rule_engine import RuleEngine
from auto_cell.l1.state_machine import RecipeStateMachine
from auto_cell.l1.types import (
    ActionCandidate,
    Context,
    CycleResult,
    Recipe,
    Rule,
)
from auto_cell.plugins.cell_culture.environment import CellCultureEnv
from auto_cell.plugins.cell_culture.events import detect_events


class RecipeEngine:
    """One-cycle Decide step for the L1 closed-loop."""

    def __init__(
        self,
        recipe: Recipe,
        rules: list[Rule],
        suppression_defaults: dict[str, float],
        approvals: dict[str, str] | None = None,
    ) -> None:
        self.recipe = recipe
        self.rules = rules
        self.approvals = approvals or {}
        self._cycle_interval_hours = 30.0 / 3600.0

        self.context = Context(
            recipe=recipe,
            env=None,
            elapsed_hours=0.0,
            state_id=recipe.initial_state,
            event_log=[],
            approvals=self.approvals,
        )
        self.state_machine = RecipeStateMachine(recipe, self.context)
        # Queue entry actions of the initial state so they are emitted on the first step.
        initial_state = recipe.get_state(recipe.initial_state)
        self.state_machine.pending_entry_actions.extend(initial_state.entry_actions)
        self.rule_engine = RuleEngine(rules, self.recipe)
        self.dispatcher = EventDispatcher(suppression_defaults)
        self.planner = ActionPlanner()

    @classmethod
    def from_files(
        cls,
        recipe_path: str,
        rules_path: str,
        suppression_defaults: dict[str, float] | None = None,
        approvals: dict[str, str] | None = None,
    ) -> "RecipeEngine":
        recipe = load_recipe(recipe_path)
        rules = load_rules(rules_path)
        return cls(recipe, rules, suppression_defaults or {}, approvals)

    def step(self, cycle: int, elapsed_hours: float, env: CellCultureEnv) -> CycleResult:
        self.context = self.context.model_copy(
            update={"env": env, "elapsed_hours": elapsed_hours}
        )
        self.state_machine.context = self.context
        self.state_machine.evaluator.context = self.context

        # 1. Events
        raw_events = detect_events(env)
        active_events = self.dispatcher.update(raw_events, elapsed_hours)
        self.context.event_log = active_events
        self.state_machine.context = self.context
        self.state_machine.evaluator.context = self.context

        # 2. Recipe actions from previously entered state
        recipe_candidates = self._collect_recipe_actions(elapsed_hours)

        # 3. State transitions
        transitions = self.state_machine.evaluate_transitions(elapsed_hours)
        if transitions:
            chosen = transitions[0]
            self.state_machine.to_state(chosen, elapsed_hours=elapsed_hours)
            self.context = self.context.model_copy(update={"state_id": chosen})

        # 4. Timeouts
        timeout_target = self.state_machine.apply_timeout(elapsed_hours)
        if timeout_target:
            self.state_machine.to_state(timeout_target, elapsed_hours=elapsed_hours)
            self.context = self.context.model_copy(update={"state_id": timeout_target})

        # 5. Recipe actions from newly entered state (same cycle)
        recipe_candidates.extend(self._collect_recipe_actions(elapsed_hours))

        # 5. Rule actions
        rule_candidates = self.rule_engine.evaluate(
            env, active_events, elapsed_hours, self.approvals
        )

        # 6. Planning
        all_candidates = recipe_candidates + rule_candidates
        executed, rejected, approval_requested = self.planner.plan(
            all_candidates, env, self.context.state_id, self.context
        )

        return CycleResult(
            cycle=cycle,
            elapsed_hours=elapsed_hours,
            state_id=self.context.state_id,
            sensor_snapshot=env,
            events=active_events,
            candidates=all_candidates,
            executed=executed,
            rejected=rejected,
            approval_requested=approval_requested,
        )

    def _collect_recipe_actions(self, elapsed_hours: float) -> list[ActionCandidate]:
        state = self.recipe.get_state(self.context.state_id)
        actions: list[ActionCandidate] = []

        for tc in self.state_machine.pending_entry_actions:
            actions.append(
                ActionCandidate(
                    source="recipe:entry",
                    priority="P2",
                    action=tc,
                    reason="state entry",
                )
            )
        self.state_machine.pending_entry_actions.clear()

        for sched in state.scheduled_actions:
            if self._is_due(sched, elapsed_hours):
                actions.append(
                    ActionCandidate(
                        source="recipe:scheduled",
                        priority="P2",
                        action=sched.action,
                        reason=f"scheduled every_hours={sched.every_hours}",
                    )
                )
        return actions

    def _is_due(self, sched, elapsed_hours: float) -> bool:
        if sched.every_hours is not None:
            return elapsed_hours % sched.every_hours < self._cycle_interval_hours
        if sched.every_minutes is not None:
            return elapsed_hours % (sched.every_minutes / 60.0) < self._cycle_interval_hours
        if sched.at_hours is not None:
            return any(abs(elapsed_hours - h) < self._cycle_interval_hours for h in sched.at_hours)
        return False
