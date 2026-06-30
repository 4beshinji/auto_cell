"""Tests for the high-level aggregate imaging service."""

from __future__ import annotations

import numpy as np
import pytest
from skimage.draw import disk
from skimage.measure import label

from auto_cell.plugins.cell_culture.aggregate_imaging_service import (
    AggregateImagingService,
)
from auto_cell.plugins.cell_culture.environment import CellCultureEnv


def _synthetic_mask() -> np.ndarray:
    img = np.zeros((1024, 1024), dtype=np.uint8)
    # Diameters: 200 px, 400 px, 500 px (pixel_size_um=2 -> 400, 800, 1000 µm)
    for center, radius in [((150, 150), 50), ((500, 500), 100), ((850, 850), 125)]:
        rr, cc = disk(center, radius, shape=img.shape)
        img[rr, cc] = 255
    return label(img > 0)


def test_service_processes_mask(tmp_path: pytest.TempPathFactory) -> None:
    masks = _synthetic_mask()
    service = AggregateImagingService(
        pixel_size_um=2.0,
        large_threshold_um=400.0,
        artifact_dir=tmp_path,
    )
    env = CellCultureEnv(
        vcd=10e6,
        viability_pct=95.0,
        glucose_mM=5.0,
        lactate_mM=5.0,
        glutamine_mM=2.0,
        ph=7.1,
        do_pct=40.0,
        temp_c=37.0,
        osmolality_mOsm_kg=300.0,
        agitation_rpm=80.0,
        perfusion_rate_vvd=3.0,
        culture_age_d=3.0,
    )

    metrics, _, events = service.process(
        masks, env, run_id="run_1", sample_id="sample_A", is_mask=True
    )

    assert metrics.n_objects == 3
    assert metrics.mean_diameter_um > 0
    assert env.aggregate_diameter_um == metrics.mean_diameter_um
    assert env.large_aggregate_ratio == metrics.large_aggregate_ratio
    assert any(e.event_id == "large_aggregate_high" for e in events)


def test_service_detects_out_of_range_event() -> None:
    masks = _synthetic_mask()
    service = AggregateImagingService(
        pixel_size_um=2.0,
        large_threshold_um=400.0,
    )
    env = CellCultureEnv(
        vcd=10e6,
        viability_pct=95.0,
        glucose_mM=5.0,
        lactate_mM=5.0,
        glutamine_mM=2.0,
        ph=7.1,
        do_pct=40.0,
        temp_c=37.0,
        osmolality_mOsm_kg=300.0,
        agitation_rpm=80.0,
        perfusion_rate_vvd=3.0,
        culture_age_d=3.0,
    )

    metrics, _, events = service.process(
        masks, env, run_id="run_1", sample_id="sample_A", is_mask=True
    )

    event_ids = {e.event_id for e in events}
    assert "aggregate_out_of_range" in event_ids
    assert "large_aggregate_high" in event_ids


def test_service_updates_env_fields() -> None:
    img = np.zeros((256, 256), dtype=np.uint8)
    rr, cc = disk((128, 128), 50, shape=img.shape)
    img[rr, cc] = 255
    masks = label(img > 0)

    service = AggregateImagingService(pixel_size_um=2.0)
    env = CellCultureEnv(
        vcd=10e6,
        viability_pct=95.0,
        glucose_mM=5.0,
        lactate_mM=5.0,
        glutamine_mM=2.0,
        ph=7.1,
        do_pct=40.0,
        temp_c=37.0,
        osmolality_mOsm_kg=300.0,
        agitation_rpm=80.0,
        perfusion_rate_vvd=3.0,
        culture_age_d=3.0,
    )

    metrics, _, _ = service.process(
        masks, env, run_id="run_1", sample_id="sample_B", is_mask=True
    )

    assert env.aggregate_diameter_um == pytest.approx(
        metrics.mean_diameter_um, abs=1e-6
    )
    assert env.circularity == pytest.approx(metrics.mean_circularity, abs=1e-6)
    assert env.aspect_ratio == pytest.approx(metrics.mean_aspect_ratio, abs=1e-6)
