"""Tests for the quality dimension and grade models."""

from __future__ import annotations

from nexusai.domain.model.quality import QualityDimension, QualityGrade


def test_dimensions_have_expected_values() -> None:
    assert QualityDimension.COMPLETENESS.value == "completeness"
    assert {dimension.value for dimension in QualityDimension} == {
        "completeness",
        "accuracy",
        "consistency",
        "uniqueness",
        "integrity",
        "timeliness",
    }


def test_grades_are_ordered() -> None:
    assert QualityGrade.A > QualityGrade.B
    assert QualityGrade.F < QualityGrade.D
    assert QualityGrade.C <= QualityGrade.C
    assert QualityGrade.B <= QualityGrade.A


def test_grade_rank_is_monotonic() -> None:
    order = (QualityGrade.F, QualityGrade.D, QualityGrade.C, QualityGrade.B, QualityGrade.A)
    ranks = [grade.rank for grade in order]
    assert ranks == sorted(ranks)
