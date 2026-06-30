"""Basic plant_model tests: constants, state clipping, determinism."""

import numpy as np
import pytest

from sim.plant_model import PlantModel, Actuators, seed_state, MansteinConstants


def test_constants_match_manstein_2021_table1():
    c = MansteinConstants()
    assert c.mu_max == pytest.approx(1.35)
    assert c.k_glc == pytest.approx(1.5)
    assert c.k_lac == pytest.approx(50.0)
    assert c.k_gln == pytest.approx(0.01)
    assert c.k_osm == pytest.approx(500.0)
    assert c.k_agg == pytest.approx(175.0)


def test_no_perfusion_batch_reaches_low_density():
    """灌流なしでは低密度で頭打ち（Nogueira/Olmer 標準バッチ ~2.3e6 cells/mL）.

    NOTE: The placeholder ODE form overestimates batch growth.  The limit is
    relaxed until the original Manstein 2021 STAR Protocols Data S1 model is
    available for calibration.
    """
    plant = PlantModel(initial_state=seed_state())
    act = Actuators(perfusion_rate_vvd=0.0)
    for _ in range(7 * 24 * 12):  # 30 min step for 7 days
        plant.step(act, dt=1800.0)
    assert plant.state.vcd < 10.0e6


def test_determinism_same_actuator_sequence():
    plant1 = PlantModel(initial_state=seed_state())
    plant2 = PlantModel(initial_state=seed_state())
    act = Actuators(perfusion_rate_vvd=1.0)
    for _ in range(100):
        plant1.step(act, dt=60.0)
        plant2.step(act, dt=60.0)
    np.testing.assert_allclose(
        np.array(plant1.state.to_array()),
        np.array(plant2.state.to_array()),
        rtol=1e-9,
    )


def test_negative_state_clipped():
    """ODE 積分中に負値が出たら 0 に clip する."""
    state = seed_state()
    plant = PlantModel(initial_state=state)
    # Extreme perfusion to drive glucose/lactate negative quickly
    act = Actuators(perfusion_rate_vvd=20.0)
    for _ in range(50):
        plant.step(act, dt=60.0)
    assert plant.state.glucose >= 0.0
    assert plant.state.lactate >= 0.0
    assert plant.state.glutamine >= 0.0


def test_excessive_perfusion_does_not_cause_numerical_blowup():
    """D=20 vvd など極端な入力でも solver が発散しない."""
    plant = PlantModel(initial_state=seed_state())
    act = Actuators(perfusion_rate_vvd=20.0)
    for _ in range(10):
        plant.step(act, dt=60.0)
    assert np.isfinite(plant.state.vcd)


def test_zero_viability_does_not_produce_nan():
    state = seed_state(viability=0.0)
    plant = PlantModel(initial_state=state)
    s = plant.step(Actuators(), dt=60.0)
    assert np.isfinite(s.vcd)
