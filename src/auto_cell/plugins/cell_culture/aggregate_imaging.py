"""At-line brightfield/phase-contrast aggregate image analysis.

Cellpose is imported lazily so that environments without a GPU (or without the
heavy cellpose dependency) can still import the module and use the fallback
metrics helpers on pre-segmented masks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from pydantic import BaseModel
from skimage.measure import regionprops


class AggregateMetrics(BaseModel):
    """Metrics describing aggregate morphology in one image."""

    mean_diameter_um: float
    large_aggregate_ratio: float  # fraction > large_threshold_um
    mean_circularity: float
    mean_aspect_ratio: float
    n_objects: int
    pixel_size_um: float


class AggregateAnalyzer:
    """Cellpose-based aggregate segmentation with scikit-image fallback."""

    def __init__(
        self,
        pixel_size_um: float = 1.0,
        model_type: str = "cyto3",
        diameter_px: float = 150.0,
        large_threshold_um: float = 400.0,
    ):
        self.pixel_size_um = pixel_size_um
        self.model_type = model_type
        self.diameter_px = diameter_px
        self.large_threshold_um = large_threshold_um
        self._model: Any | None = None

    def _cellpose_model(self) -> Any:
        """Lazy-load Cellpose model."""
        if self._model is None:
            from cellpose import models

            self._model = models.Cellpose(model_type=self.model_type)
        return self._model

    def _compute_metrics(
        self, masks: np.ndarray
    ) -> AggregateMetrics:
        """Compute metrics from a labeled mask (no Cellpose required)."""
        regions = regionprops(masks)
        if not regions:
            return AggregateMetrics(
                mean_diameter_um=0.0,
                large_aggregate_ratio=0.0,
                mean_circularity=0.0,
                mean_aspect_ratio=0.0,
                n_objects=0,
                pixel_size_um=self.pixel_size_um,
            )

        diameters: list[float] = []
        circularities: list[float] = []
        aspect_ratios: list[float] = []

        for r in regions:
            diameters.append(r.equivalent_diameter_area * self.pixel_size_um)
            if r.perimeter and r.perimeter > 0:
                circularities.append(
                    4.0 * np.pi * r.area / (r.perimeter**2)
                )
            if hasattr(r, "axis_minor_length") and r.axis_minor_length > 0:
                aspect_ratios.append(
                    r.axis_major_length / r.axis_minor_length
                )
            elif hasattr(r, "minor_axis_length") and r.minor_axis_length > 0:
                aspect_ratios.append(
                    r.major_axis_length / r.minor_axis_length
                )

        large_count = sum(1 for d in diameters if d > self.large_threshold_um)

        return AggregateMetrics(
            mean_diameter_um=float(np.mean(diameters)),
            large_aggregate_ratio=large_count / len(diameters),
            mean_circularity=float(np.mean(circularities))
            if circularities
            else 0.0,
            mean_aspect_ratio=float(np.mean(aspect_ratios))
            if aspect_ratios
            else 0.0,
            n_objects=len(regions),
            pixel_size_um=self.pixel_size_um,
        )

    def analyze(
        self, image: np.ndarray
    ) -> tuple[AggregateMetrics, np.ndarray]:
        """Analyze a raw image and return metrics plus the segmentation mask.

        ``image`` may be (H, W) or (H, W, C) uint8/uint16.
        """
        masks, *_ = self._cellpose_model().eval(
            image,
            channels=[0, 0] if image.ndim == 2 else [0, 0],
            diameter=self.diameter_px,
        )
        return self._compute_metrics(masks), masks

    def analyze_mask(self, masks: np.ndarray) -> AggregateMetrics:
        """Compute metrics directly from an existing labeled mask.

        This avoids the Cellpose dependency in tests and lightweight pipelines.
        """
        return self._compute_metrics(masks)

    def save_artifact(
        self,
        raw_image: np.ndarray,
        masks: np.ndarray,
        metrics: AggregateMetrics,
        run_id: str,
        sample_id: str,
        out_dir: Path,
    ) -> Path:
        """Persist raw image, mask, and metrics for audit/traceability."""
        sample_dir = Path(out_dir) / run_id / sample_id
        sample_dir.mkdir(parents=True, exist_ok=True)

        Image.fromarray(raw_image).save(sample_dir / "raw.png")
        # Pseudo-color mask by label modulo 256.
        mask_color = (masks % 256).astype(np.uint8)
        Image.fromarray(mask_color, mode="L").save(sample_dir / "mask.png")
        (sample_dir / "metrics.json").write_text(
            json.dumps(metrics.model_dump(), indent=2),
            encoding="utf-8",
        )
        return sample_dir
