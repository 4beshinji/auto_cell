"""ODE right-hand side for the Manstein 2021 iPSC perfusion model."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .constants import MansteinConstants
from .state import Actuators, PlantState


@dataclass(frozen=True)
class FeedComposition:
    """Perfusion feed medium composition at a given process day."""

    glucose: float       # mM
    glutamine: float     # mM
    osmolality: float    # mOsm/kg


def select_feed(t_day: float, constants: MansteinConstants) -> FeedComposition:
    """Return feed composition based on process day (Manstein protocol)."""
    if t_day < 1.0:
        return FeedComposition(
            glucose=constants.feed_glc_i,
            glutamine=constants.feed_gln,
            osmolality=constants.feed_osm,
        )
    if t_day < 4.0:
        return FeedComposition(
            glucose=constants.feed_glc_i,
            glutamine=constants.feed_gln,
            osmolality=constants.feed_osm,
        )
    return FeedComposition(
        glucose=constants.feed_glc_ii,
        glutamine=constants.feed_gln_ii,
        osmolality=constants.feed_osm,
    )


def manstein_rhs(
    t: float,
    y: NDArray[np.float64],
    actuators: Actuators,
    constants: MansteinConstants,
    feed: FeedComposition,
) -> NDArray[np.float64]:
    """6 項 Monod ODE の右辺."""
    state = PlantState.from_array(y)
    X = state.vcd
    G = state.glucose
    L = state.lactate
    Q = state.glutamine
    Osm = state.osmolality
    d = state.aggregate_diameter
    D = actuators.perfusion_rate_vvd

    # Monod terms
    # NOTE: The D/(K_Perf+D) term follows M01 and acts as a perfusion
    # limitation/enhancement multiplier.  It is a placeholder until the
    # original Berkeley Madonna code (STAR Protocols Data S1) can be obtained
    # and the right-hand side recalibrated.
    mu_eff = (
        constants.mu_max
        * (G / (constants.k_glc + G))
        * (constants.k_lac / (constants.k_lac + L))
        * (Q / (constants.k_gln + Q))
        * (constants.k_osm / (constants.k_osm + Osm))
        * (constants.k_agg / (constants.k_agg + d))
        * (D / (0.5 + D))          # K_Perf placeholder; to be calibrated against Data S1
    )

    # Mass balance
    # Viability reduces effective growth; a culture with 0% viability cannot grow.
    dXdt = mu_eff * X * (state.viability / 100.0)
    dvdt = 0.0
    # NOTE: feed_glucose / feed_glutamine bolus actuators are not modeled here.
    # They are accepted by the Actuators dataclass for API compatibility but have
    # no effect until a bolus-injection term is calibrated and added.
    dGdt = D * (feed.glucose - G) - constants.q_glc * X
    dLdt = constants.q_lac * X - D * L
    dQdt = D * (feed.glutamine - Q) - constants.q_gln * X - 0.003 * Q

    # Osmolality: simplified; replace after Data S1 review
    base_rate = 0.0 if actuators.ph_setpoint >= 7.0 else 5.0  # placeholder
    dOdt = D * (feed.osmolality - Osm) + 1.0 * dLdt + base_rate

    # Aggregate growth
    dddt = constants.agg_growth * mu_eff * d

    return np.array([dXdt, dvdt, dGdt, dLdt, dQdt, dOdt, dddt])
