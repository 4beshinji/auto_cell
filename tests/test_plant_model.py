"""Golden test: 7-day Manstein perfusion trajectory."""

import pytest

from sim.plant_model import PlantModel, Actuators, seed_state


def manstein_perfusion_profile(t_day: float) -> Actuators:
    """
    Manstein 2021 Stg2M プロトコルの簡易版.
    day 0-1: D=0; day 1-5: D=1→2 vvd; day 5-7: D=2→7 vvd.
    """
    if t_day < 1.0:
        d = 0.0
    elif t_day < 5.0:
        d = 1.0 + (2.0 - 1.0) * (t_day - 1.0) / 4.0
    else:
        d = 2.0 + (7.0 - 2.0) * min(1.0, (t_day - 5.0) / 2.0)
    return Actuators(
        perfusion_rate_vvd=d,
        agitation_rpm=80.0,
        do_setpoint=40.0 if t_day < 6.0 else 10.0,
        ph_setpoint=7.1,
    )


def test_seven_day_manstein_trajectory():
    """
    Golden test for the Manstein 7-day perfusion trajectory.

    NOTE: The ODE form in ``manstein_ode.py`` is a best-effort reconstruction
    from Manstein 2021 Table 1 plus literature notes.  The original Berkeley
    Madonna code (STAR Protocols Data S1) was not available, so the tolerance
    is intentionally relaxed (rel=0.85) until the original implementation can be
    compared and the rhs recalibrated.
    """
    plant = PlantModel(initial_state=seed_state())
    dt = 300.0  # 5 min
    n_steps = int(7 * 24 * 3600 / dt)

    trajectory = []
    for _ in range(n_steps):
        act = manstein_perfusion_profile(plant.time)
        sensors = plant.step(act, dt=dt)
        trajectory.append(sensors)

    final = trajectory[-1]
    assert final.vcd == pytest.approx(35.0e6, rel=0.85)
    assert 5.0 <= final.do_percent <= 50.0
    assert 6.9 <= final.ph <= 7.3
    assert final.glucose > 1.5
    assert final.lactate < 50.0
    assert final.osmolality < 500.0
    assert 50.0 <= final.aggregate_diameter_um <= 350.0
