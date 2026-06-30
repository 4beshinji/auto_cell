"""Synchronous L1 cycle executor for Phase 1."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone

from auto_cell.l1.recipe_engine import RecipeEngine
from auto_cell.l1.types import CycleResult, ToolCall
from auto_cell.plugins.cell_culture.environment import CellCultureEnv

logger = logging.getLogger(__name__)


class L1CycleExecutor:
    """Run the L1 Decide-Act loop synchronously."""

    def __init__(
        self,
        recipe_engine: RecipeEngine,
        get_env: Callable[[], CellCultureEnv],
        issue_command: Callable[[ToolCall, str], None],
        request_approval: Callable[[ToolCall, str], str],
        audit: Callable[[CycleResult], None],
        cycle_interval_seconds: float = 30.0,
    ) -> None:
        self.engine = recipe_engine
        self.get_env = get_env
        self.issue_command = issue_command
        self.request_approval = request_approval
        self.audit = audit
        self.cycle_interval_seconds = cycle_interval_seconds
        self.cycle = 0
        self.running = False

    def run_once(self) -> CycleResult:
        self.cycle += 1
        env = self.get_env()
        elapsed_hours = getattr(env, "culture_age_h", None)
        if elapsed_hours is None:
            elapsed_hours = getattr(env, "culture_age_d", 0.0) * 24.0

        result = self.engine.step(self.cycle, elapsed_hours, env)

        for tc in result.executed:
            self.issue_command(tc, f"c{self.cycle}-{tc.tool}")
            self._update_setpoint_history(env, tc)
        for tc in result.approval_requested:
            self.request_approval(tc, f"c{self.cycle}-{tc.tool}")

        self.audit(result)
        return result

    def _update_setpoint_history(self, env: CellCultureEnv, tc: ToolCall) -> None:
        if tc.tool == "set_perfusion_rate":
            env.last_perfusion_rate_vvd = tc.args.get("vvd")
        elif tc.tool == "set_agitation_rpm":
            env.last_agitation_rpm = tc.args.get("rpm")
        elif tc.tool == "set_gas_setpoint":
            gas = tc.args.get("gas")
            if gas == "do":
                env.last_do_setpoint_pct = tc.args.get("setpoint")
            elif gas == "ph":
                env.last_ph_setpoint = tc.args.get("setpoint")
            else:
                return
        else:
            return
        env.last_setpoint_at = datetime.now(timezone.utc)

    def run_blocking(self, max_cycles: int | None = None) -> None:
        self.running = True
        consecutive_errors = 0
        max_consecutive_errors = 5
        while self.running:
            try:
                self.run_once()
                consecutive_errors = 0
            except Exception:
                logger.exception("L1 cycle %s failed", self.cycle)
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("too many consecutive L1 cycle errors; stopping loop")
                    self.running = False
                    raise
            if max_cycles is not None and self.cycle >= max_cycles:
                break
            time.sleep(self.cycle_interval_seconds)

    def stop(self) -> None:
        self.running = False
