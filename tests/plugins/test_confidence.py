"""Tests for confidence score layer."""

from __future__ import annotations

import pytest

from auto_cell.plugins.cell_culture.confidence import (
    ConfidenceInput,
    ConfidenceScorer,
)


def test_gp_high_variance_low_confidence():
    scorer = ConfidenceScorer(gp_max_var=1.0, low_confidence_threshold=0.6)
    inp = ConfidenceInput(model_type="gp", posterior_variance=1.0)
    assert scorer.compute(inp) == pytest.approx(0.0, abs=1e-9)
    assert scorer.should_escalate_to_hitl(inp) is True


def test_gp_zero_variance_full_confidence():
    scorer = ConfidenceScorer(gp_max_var=1.0, low_confidence_threshold=0.6)
    inp = ConfidenceInput(model_type="gp", posterior_variance=0.0)
    assert scorer.compute(inp) == pytest.approx(1.0, abs=1e-9)
    assert scorer.should_escalate_to_hitl(inp) is False


def test_pls_q_residual_only():
    scorer = ConfidenceScorer(pls_q_ref=2.0)
    inp = ConfidenceInput(model_type="pls", q_residual=1.0)
    assert scorer.compute(inp) == pytest.approx(0.75, abs=1e-9)


def test_pls_with_hotelling():
    scorer = ConfidenceScorer(pls_q_ref=2.0)
    inp = ConfidenceInput(model_type="pls", q_residual=0.0, hotelling_t2=50.0)
    assert scorer.compute(inp) == pytest.approx(0.75, abs=1e-9)


def test_dl_mc_dropout():
    scorer = ConfidenceScorer(dl_std_ref=0.5)
    inp = ConfidenceInput(model_type="dl", mc_dropout_std=0.25)
    assert scorer.compute(inp) == pytest.approx(0.75, abs=1e-9)


def test_dl_with_ood():
    scorer = ConfidenceScorer(dl_std_ref=0.5)
    inp = ConfidenceInput(model_type="dl", mc_dropout_std=0.0, ood_score=0.2)
    assert scorer.compute(inp) == pytest.approx(0.9, abs=1e-9)


def test_invalid_model_type_raises():
    scorer = ConfidenceScorer()
    with pytest.raises(ValueError):
        scorer.compute(ConfidenceInput(model_type="unknown"))


def test_gp_max_var_avoids_division_by_zero():
    scorer = ConfidenceScorer(gp_max_var=0.0)
    inp = ConfidenceInput(model_type="gp", posterior_variance=0.0)
    assert scorer.compute(inp) == pytest.approx(1.0, abs=1e-9)
