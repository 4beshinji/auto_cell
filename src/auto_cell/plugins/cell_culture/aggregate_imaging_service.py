"""High-level service integrating aggregate image analysis into L1/L2.

The service wraps ``AggregateAnalyzer`` and provides env updates, event
generation, and artifact persistence so that at-line images can feed the
deterministic L1 rule engine and the L2 Bayesian optimization loop.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

from auto_cell.plugins.cell_culture.aggregate_imaging import (
    AggregateAnalyzer,
    AggregateMetrics,
)
from auto_cell.plugins.cell_culture.environment import CellCultureEnv, CppEnvelope
from auto_cell.plugins.cell_culture.events import CultureEvent


class AggregateImagingService:
    """Analyze aggregate images and push metrics into the control loop."""

    def __init__(
        self,
        *,
        pixel_size_um: float = 1.0,
        model_type: str = "cyto3",
        diameter_px: float = 150.0,
        large_threshold_um: float = 400.0,
        artifact_dir: str | Path | None = None,
    ) -> None:
        self.analyzer = AggregateAnalyzer(
            pixel_size_um=pixel_size_um,
            model_type=model_type,
            diameter_px=diameter_px,
            large_threshold_um=large_threshold_um,
        )
        self.artifact_dir = Path(artifact_dir) if artifact_dir else None

    def analyze_image(
        self, image: np.ndarray | str | Path
    ) -> tuple[AggregateMetrics, np.ndarray]:
        """Analyze a raw image and return metrics plus the segmentation mask.

        ``image`` may be an ndarray or a path to a PNG/TIFF file.
        """
        if isinstance(image, (str, Path)):
            arr = np.array(Image.open(image))
        else:
            arr = image
        return self.analyzer.analyze(arr)

    def analyze_mask(self, masks: np.ndarray) -> AggregateMetrics:
        """Compute metrics from an existing labeled mask (Cellpose-free)."""
        return self.analyzer.analyze_mask(masks)

    def update_env(
        self,
        env: CellCultureEnv,
        metrics: AggregateMetrics,
    ) -> None:
        """Write aggregate metrics into ``CellCultureEnv``."""
        env.aggregate_diameter_um = metrics.mean_diameter_um
        env.large_aggregate_ratio = metrics.large_aggregate_ratio
        env.circularity = metrics.mean_circularity
        env.aspect_ratio = metrics.mean_aspect_ratio

    def detect_events(self, metrics: AggregateMetrics) -> list[CultureEvent]:
        """Fire aggregate-related events from image-derived metrics."""
        events: list[CultureEvent] = []
        now = datetime.now(timezone.utc)
        e = CppEnvelope

        d = metrics.mean_diameter_um
        if d < e.AGGREGATE_MEAN_WARNING[0] or d > e.AGGREGATE_MEAN_WARNING[1]:
            events.append(
                CultureEvent(
                    event_id="aggregate_out_of_range",
                    priority="P2",
                    message="凝集体平均径が目標範囲外（150–350 µm）。",
                    source_field="aggregate_diameter_um",
                    measured_at=now,
                    suppression_window_s=int(
                        600 / 3600.0 * 3600
                    ),
                )
            )

        if metrics.large_aggregate_ratio >= e.LARGE_AGGREGATE_WARNING:
            events.append(
                CultureEvent(
                    event_id="large_aggregate_high",
                    priority="P2",
                    message="大径凝集体（>400 µm）割合が高い（>15%）。",
                    source_field="large_aggregate_ratio",
                    measured_at=now,
                    suppression_window_s=int(
                        600 / 3600.0 * 3600
                    ),
                )
            )

        return events

    def process(
        self,
        image: np.ndarray | str | Path,
        env: CellCultureEnv,
        run_id: str,
        sample_id: str,
        *,
        is_mask: bool = False,
    ) -> tuple[AggregateMetrics, np.ndarray, list[CultureEvent]]:
        """Analyze an image or mask, update env, detect events, and save artifacts.

        Args:
            image: Raw image or labeled mask array, or a path to a raw image.
            env: Culture environment to update.
            run_id: Run identifier for artifact storage.
            sample_id: Sample identifier for artifact storage.
            is_mask: If True, ``image`` is treated as a labeled mask.
        """
        if isinstance(image, (str, Path)):
            raw_image = np.array(Image.open(image))
            metrics, masks = self.analyze_image(image)
        elif is_mask:
            raw_image = image
            masks = image
            metrics = self.analyze_mask(image)
        else:
            raw_image = image
            metrics, masks = self.analyze_image(image)

        self.update_env(env, metrics)
        events = self.detect_events(metrics)

        if self.artifact_dir is not None:
            self.analyzer.save_artifact(
                raw_image, masks, metrics, run_id, sample_id, self.artifact_dir
            )

        return metrics, masks, events
