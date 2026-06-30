"""Confidence score layer for AI/statistical model outputs.

Conforms to ADR-0001 §9.3: low-confidence AI outputs are escalated to HITL.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch
from pydantic import BaseModel, Field


class ConfidenceInput(BaseModel):
    """Inputs for computing a confidence score."""

    model_type: str = Field(..., pattern="^(gp|pls|dl)$")
    # GP-specific
    posterior_variance: float | None = None
    # PLS-specific
    q_residual: float | None = None
    hotelling_t2: float | None = None
    # DL-specific
    mc_dropout_std: float | None = None
    ood_score: float | None = None


class ConfidenceScorer:
    """Normalize model-specific uncertainty metrics to a [0, 1] score.

    Higher is more confident. A score below ``low_confidence_threshold`` triggers
    HITL escalation via ``should_escalate_to_hitl()``.
    """

    def __init__(
        self,
        gp_max_var: float = 1.0,
        pls_q_ref: float = 1.0,
        dl_std_ref: float = 1.0,
        low_confidence_threshold: float = 0.6,
    ):
        self.gp_max_var = gp_max_var
        self.pls_q_ref = pls_q_ref
        self.dl_std_ref = dl_std_ref
        self.threshold = low_confidence_threshold

    def from_gp_variance(self, variance: float) -> float:
        """variance → 0 yields confidence → 1."""
        std = max(variance, 0.0) ** 0.5
        return max(0.0, 1.0 - std / max(self.gp_max_var, 1e-12))

    def from_pls(
        self, q_residual: float, hotelling_t2: float | None = None
    ) -> float:
        c_q = max(0.0, 1.0 - q_residual / max(self.pls_q_ref, 1e-12))
        c_t2 = 1.0 if hotelling_t2 is None else max(
            0.0, 1.0 - hotelling_t2 / 100.0
        )
        return float(np.clip((c_q + c_t2) / 2.0, 0.0, 1.0))

    def from_dl(self, mc_std: float, ood: float | None = None) -> float:
        c_std = max(0.0, 1.0 - mc_std / max(self.dl_std_ref, 1e-12))
        c_ood = 1.0 if ood is None else max(0.0, 1.0 - ood)
        return float(np.clip((c_std + c_ood) / 2.0, 0.0, 1.0))

    def compute(self, inp: ConfidenceInput) -> float:
        if inp.model_type == "gp":
            return self.from_gp_variance(inp.posterior_variance or 0.0)
        if inp.model_type == "pls":
            return self.from_pls(
                inp.q_residual or 0.0,
                inp.hotelling_t2,
            )
        if inp.model_type == "dl":
            return self.from_dl(
                inp.mc_dropout_std or 0.0,
                inp.ood_score,
            )
        raise ValueError(f"Unknown model_type: {inp.model_type}")

    def should_escalate_to_hitl(self, inp: ConfidenceInput) -> bool:
        return self.compute(inp) < self.threshold


def confidence_from_bo_candidate(
    optimizer: Any, params: dict[str, Any]
) -> float:
    """Extract posterior variance from an Ax/BoTorch model for a candidate.

    Returns 1.0 (no escalation) when the surrogate model is not yet available,
    e.g. during Sobol initialization.
    """
    try:
        model_bridge = optimizer.ax.generation_strategy.model
        if model_bridge is None:
            return 1.0

        botorch_model = getattr(model_bridge, "model", None)
        if botorch_model is None:
            return 1.0

        # Parameter order is the search space order.
        param_names = list(params.keys())
        x = torch.tensor(
            [[params[p] for p in param_names]], dtype=torch.double
        )
        with torch.no_grad():
            posterior = botorch_model.posterior(x)
            var = posterior.variance.squeeze().item()

        scorer = ConfidenceScorer()
        return scorer.from_gp_variance(var)
    except Exception:
        # Any failure to extract variance should not block the workflow.
        return 1.0
