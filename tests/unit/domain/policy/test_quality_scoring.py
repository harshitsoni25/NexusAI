"""Tests for the pure quality-scoring policy."""

from __future__ import annotations

from nexusai.domain.model.assessment import QualityMeasurement
from nexusai.domain.model.quality import QualityGrade
from nexusai.domain.policy.quality_scoring import QualityScorer


def _measure(score: float, weight: float = 1.0) -> QualityMeasurement:
    return QualityMeasurement(dimension="d", score=score, weight=weight)


def test_composite_is_weighted_mean() -> None:
    scorer = QualityScorer()
    composite = scorer.composite([_measure(1.0, 3.0), _measure(0.0, 1.0)])
    assert composite == 0.75


def test_composite_of_nothing_is_zero() -> None:
    assert QualityScorer().composite([]) == 0.0


def test_composite_with_zero_weight_is_zero() -> None:
    assert QualityScorer().composite([_measure(1.0, 0.0)]) == 0.0


def test_default_grade_bands() -> None:
    scorer = QualityScorer()
    assert scorer.grade_for(0.95) is QualityGrade.A
    assert scorer.grade_for(0.85) is QualityGrade.B
    assert scorer.grade_for(0.75) is QualityGrade.C
    assert scorer.grade_for(0.65) is QualityGrade.D
    assert scorer.grade_for(0.40) is QualityGrade.F


def test_boundary_scores_round_up() -> None:
    scorer = QualityScorer()
    assert scorer.grade_for(0.90) is QualityGrade.A
    assert scorer.grade_for(0.60) is QualityGrade.D


def test_custom_bands_are_reordered() -> None:
    scorer = QualityScorer(bands=((0.5, QualityGrade.C), (0.8, QualityGrade.A)))
    # Even though supplied out of order, the highest threshold wins first.
    assert scorer.grade_for(0.85) is QualityGrade.A
    assert scorer.grade_for(0.6) is QualityGrade.C


def test_score_returns_result_and_grade() -> None:
    result, grade = QualityScorer().score([_measure(0.95, 2.0), _measure(0.85, 1.0)])
    assert round(result.composite_score, 4) == 0.9167
    assert grade is QualityGrade.A
