"""Tests for aggregate imaging analysis (Cellpose-free path)."""

from __future__ import annotations

import numpy as np
import pytest
from skimage.draw import disk
from skimage.measure import label

from auto_cell.plugins.cell_culture.aggregate_imaging import AggregateAnalyzer


def test_metrics_on_synthetic_disks():
    """Synthetic mask: verify diameters and large-aggregate ratio."""
    analyzer = AggregateAnalyzer(pixel_size_um=2.0, large_threshold_um=400.0)
    img = np.zeros((1024, 1024), dtype=np.uint8)
    # Diameters: 100 px -> 200 µm, 200 px -> 400 µm, 250 px -> 500 µm
    # Centers are spaced far apart to avoid merging.
    for center, radius in [((150, 150), 50), ((500, 500), 100), ((850, 850), 125)]:
        rr, cc = disk(center, radius, shape=img.shape)
        img[rr, cc] = 255

    masks = label(img > 0)
    metrics = analyzer.analyze_mask(masks)

    assert metrics.n_objects == 3
    assert metrics.mean_diameter_um > 0
    assert metrics.large_aggregate_ratio == pytest.approx(1 / 3, abs=0.05)


def test_empty_mask_returns_zeros():
    analyzer = AggregateAnalyzer(pixel_size_um=1.0)
    masks = np.zeros((100, 100), dtype=np.int32)
    metrics = analyzer.analyze_mask(masks)
    assert metrics.n_objects == 0
    assert metrics.mean_diameter_um == 0.0
    assert metrics.large_aggregate_ratio == 0.0


def test_circularity_of_disk():
    """A perfect disk should have circularity close to 1."""
    analyzer = AggregateAnalyzer(pixel_size_um=1.0)
    img = np.zeros((256, 256), dtype=np.uint8)
    rr, cc = disk((128, 128), 50, shape=img.shape)
    img[rr, cc] = 255
    masks = label(img > 0)
    metrics = analyzer.analyze_mask(masks)
    assert metrics.n_objects == 1
    # Digital contour approximation yields circularity slightly below 1.
    assert metrics.mean_circularity == pytest.approx(1.0, abs=0.10)
    assert metrics.mean_aspect_ratio == pytest.approx(1.0, abs=0.05)


def test_save_artifact(tmp_path):
    analyzer = AggregateAnalyzer(pixel_size_um=1.0)
    img = np.zeros((128, 128), dtype=np.uint8)
    rr, cc = disk((64, 64), 20, shape=img.shape)
    img[rr, cc] = 255
    masks = label(img > 0)
    metrics = analyzer.analyze_mask(masks)

    out = analyzer.save_artifact(img, masks, metrics, "run_1", "sample_A", tmp_path)
    assert out.exists()
    assert (out / "raw.png").exists()
    assert (out / "mask.png").exists()
    assert (out / "metrics.json").exists()
