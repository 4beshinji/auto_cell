"""Scalar run-level objective function for Bayesian optimization."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class RunMetrics(BaseModel):
    """Outcome metrics reported to BO after one run completes."""

    vcd_final: float = Field(..., description="cells/mL")
    viability_final: float = Field(..., ge=0.0, le=1.0)
    pluripotency_pct: float = Field(..., ge=0.0, le=1.0)
    mean_aggregate_diameter_um: float
    large_aggregate_ratio: float = Field(..., ge=0.0, le=1.0)
    total_run_cost: float  # cost penalty term
    max_lactate_mm: float
    max_osmolality_mosm: float


class CultureObjective:
    """J = yield × viability × pluripotency × aggregate_size × cost_penalty.

    Weights are injected from `config/bo_objective_weights.yaml` if it exists,
    otherwise a conservative default is used. Negative cost weight makes cost a
    penalty.
    """

    DEFAULT_WEIGHTS: dict[str, float] = {
        "yield": 0.30,
        "viability": 0.25,
        "pluripotency": 0.25,
        "aggregate_size": 0.10,
        "cost": -0.10,
    }
    VCD_TARGET = 35.0e6
    COST_REF = 1000.0

    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = weights or self._load_weights() or self.DEFAULT_WEIGHTS.copy()

    @classmethod
    def _load_weights(cls) -> dict[str, float] | None:
        config_path = Path("config/bo_objective_weights.yaml")
        if not config_path.exists():
            return None
        try:
            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            weights = data.get("weights")
            if isinstance(weights, dict):
                return {str(k): float(v) for k, v in weights.items()}
        except Exception:
            # Fall back to defaults on any load/parse error.
            return None
        return None

    def normalize_yield(self, vcd: float) -> float:
        return min(vcd / self.VCD_TARGET, 1.0)

    def aggregate_size_score(self, d_um: float) -> float:
        """150–350 µm is optimal; >400 µm is penalized."""
        if d_um < 150.0:
            return d_um / 150.0 * 0.8
        if d_um <= 350.0:
            return 1.0
        return max(1.0 - (d_um - 350.0) / 150.0, 0.0)

    def compute(self, m: RunMetrics) -> float:
        penalty = 0.0
        if m.max_lactate_mm > 50.0:
            penalty += 0.5 * (m.max_lactate_mm - 50.0) / 50.0
        if m.max_osmolality_mosm > 500.0:
            penalty += 0.5 * (m.max_osmolality_mosm - 500.0) / 500.0
        if m.large_aggregate_ratio > 0.20:
            penalty += 0.5 * (m.large_aggregate_ratio - 0.20) / 0.20

        score = (
            self.weights["yield"] * self.normalize_yield(m.vcd_final)
            + self.weights["viability"] * m.viability_final
            + self.weights["pluripotency"] * m.pluripotency_pct
            + self.weights["aggregate_size"]
            * self.aggregate_size_score(m.mean_aggregate_diameter_um)
            + self.weights["cost"]
            * (1.0 - min(m.total_run_cost / self.COST_REF, 1.0))
        )
        return max(score - penalty, -1.0)
