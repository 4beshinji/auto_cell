"""Tier2 plant model — literature iPSC suspension-culture kinetics (Phase 0b).

Re-implements the Monod-type in-silico process model of Manstein, Ullmann,
Triebert & Zweigerdt 2021:
  - Stem Cells Transl Med 10(7):1063-1080, "High density bioprocessing of human
    pluripotent stem cells by metabolic control and in silico modeling"
    (DOI 10.1002/sctm.20-0453, PMID 33660952) -- primary research.
  - STAR Protocols 2(4):100988 (DOI 10.1016/j.xpro.2021.100988, PMC8666714) --
    the in-silico model Table 1 (constants below).
Perfused hPSC stirred-tank culture controlling pH/DO/glucose/lactate/glutamine and
osmolality-peak suppression. Six-term Monod model.

Constants (Manstein 2021, Table 1) -- the hardcoded values ARE faithful:
  mu     = 1.35 /d          K_Glc = 1.5 mM        K_Lac = 50 mM
  K_Gln  = 0.01 mM          K_Osm = 500 mOsm/kg   K_Agg = 350/2 = 175 um (DIAMETER)
  q_Glc = 1.474e-8, q_Lac = 2.37e-8, q_Gln = 1.856e-9 mmol/cell/d
All six match this module's earlier values exactly -> no constant change needed.

Exposes ``step(actuators) -> sensors`` so the ReAct controller closes the loop
against a literature-grounded plant. NOTE: this is a PERFUSION process -- the plant
must accept a perfusion-rate input (Table 3: 0->7 vvd over days 1-7); standard batch
does not reach the target. The same interface later accepts a COBRApy+GEM or
commercial co-sim backend.

Validation target: reproduce the Manstein trajectory -- 70-fold / 7-day to
~35e6 cells/mL (150 mL = 5.25e9 cells), DO 40%->10% on days 6-7, pH 7.1.
(Standard batch reaches only ~2.3-2.4e6: Nogueira 2019 VW, Olmer 2012 stirred.)

History: an earlier P1 lit review tentatively attributed this model to Galvanauskas
et al. 2019 (Regen Therapy) and flagged the constants as "wrong"; that was a
mis-identification -- Galvanauskas is a related 3-term iPSC Monod model (glucose +
lactate + aggregate only, no glutamine/osmolality). The true source is Manstein 2021.
See docs/design/kg_to_auto_cell.md §4.1.
"""

import numpy as np
from numpy.typing import NDArray

from .constants import MansteinConstants
from .factory import seed_state, sensors_to_env
from .state import Actuators, PlantState, Sensors
from .manstein_ode import manstein_rhs, select_feed
from .solver import integrate_deterministic


__all__ = [
    "Actuators",
    "MansteinConstants",
    "PlantModel",
    "PlantState",
    "Sensors",
    "integrate_deterministic",
    "manstein_rhs",
    "seed_state",
    "select_feed",
    "sensors_to_env",
]


class PlantModelError(RuntimeError):
    """Raised when the plant model simulation cannot proceed."""


class PlantModel:
    """L1 サイクルから呼ばれる唯一の IF: step(actuators) -> sensors."""

    def __init__(
        self,
        constants: MansteinConstants | None = None,
        initial_state: PlantState | None = None,
        solver_method: str = "RK45",
        rtol: float = 1e-6,
        atol: float = 1e-9,
    ) -> None:
        self._const = constants or MansteinConstants()
        self._state = initial_state or seed_state()
        self._t: float = 0.0
        self._solver_method = solver_method
        self._rtol = rtol
        self._atol = atol

    @property
    def state(self) -> PlantState:
        return self._state

    @property
    def time(self) -> float:
        return self._t

    def step(self, actuators: Actuators, dt: float = 30.0) -> Sensors:
        """
        現在時刻から dt (seconds) だけ積分し、センサ値を返す.

        Args:
            actuators: ステップ内で一定とみなすアクチュエータ値.
            dt: 積分区間 [s]. L1 cadence は 30 s+ なので default 30 s.

        Returns:
            ステップ終了時点のセンサ値.

        Raises:
            PlantModelError: if dt is not positive or the ODE solver fails.
        """
        if dt <= 0.0:
            raise PlantModelError(f"dt must be positive, got {dt}")
        t_start = self._t
        t_end = self._t + dt / 86400.0   # 内部時刻は day
        feed = select_feed(t_start, self._const)

        def rhs(t: float, y: NDArray) -> NDArray:
            return manstein_rhs(t, y, actuators, self._const, feed)

        try:
            y_end = integrate_deterministic(
                rhs,
                self._state.to_array(),
                (t_start, t_end),
                method=self._solver_method,
                rtol=self._rtol,
                atol=self._atol,
            )
        except RuntimeError as exc:
            raise PlantModelError(f"ODE integration failed from t={t_start} to {t_end}") from exc
        self._state = PlantState.from_array(y_end)
        self._t = t_end
        return _sensors_from_state(self._state, actuators)

    def reset(self, state: PlantState | None = None) -> None:
        self._state = state or seed_state()
        self._t = 0.0

    def reset_after_passage(self) -> None:
        """Stub for passage reset; preserves API used by virtual_edge."""
        self.reset(seed_state(seeding_density=self._state.vcd * 0.1))


def _sensors_from_state(state: PlantState, actuators: Actuators) -> Sensors:
    return Sensors(
        vcd=state.vcd,
        viability=state.viability,
        glucose=state.glucose,
        lactate=state.lactate,
        glutamine=state.glutamine,
        osmolality=state.osmolality,
        aggregate_diameter_um=state.aggregate_diameter,
        do_percent=actuators.do_setpoint,
        ph=actuators.ph_setpoint,
        temp_c=37.0,
    )
