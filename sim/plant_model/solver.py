"""Deterministic ODE solver wrapper around scipy.integrate.solve_ivp."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_ivp


def integrate_deterministic(
    rhs: Callable[[float, NDArray[np.float64]], NDArray[np.float64]],
    y0: NDArray[np.float64],
    t_span: tuple[float, float],
    method: str = "RK45",
    rtol: float = 1e-6,
    atol: float = 1e-9,
) -> NDArray[np.float64]:
    """
    決定的な ODE 積分.

    - scipy.solve_ivp を使う.
    - dense_output は使わず終点値のみ返す.
    - solver 内で乱数を使わない.
    """
    sol = solve_ivp(
        rhs,
        t_span,
        y0,
        method=method,
        rtol=rtol,
        atol=atol,
        dense_output=False,
    )
    if not sol.success:
        raise RuntimeError(f"ODE integration failed: {sol.message}")
    return sol.y[:, -1]
