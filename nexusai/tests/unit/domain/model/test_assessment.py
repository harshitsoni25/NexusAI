"""Tests for validation and quality result containers."""

from __future__ import annotations

import pytest

from nexusai.domain.model.assessment import (
    QualityMeasurement,
    QualityResult,
    Severity,
    ValidationIssue,
    ValidationResult,
)


def _issue(severity: Severity, code: str = "code") -> ValidationIssue:
    return ValidationIssue(code=code, message="m", severity=severity)


def test_severity_is_ordered() -> None:
    assert Severity.INFO < Severity.WARNING < Severity.ERROR < Severity.CRITICAL
    assert Severity.ERROR <= Severity.ERROR


def test_result_is_valid_with_only_warnings() -> None:
    result = ValidationResult(issues=[_issue(Severity.WARNING), _issue(Severity.INFO)])
    assert result.is_valid is True
    assert result.highest_severity is Severity.WARNING


def test_result_invalid_with_error_or_above() -> None:
    assert ValidationResult(issues=[_issue(Severity.ERROR)]).is_valid is False
    assert ValidationResult(issues=[_issue(Severity.CRITICAL)]).is_valid is False


def test_empty_result_is_valid_with_no_highest_severity() -> None:
    result = ValidationResult.passing(checked=5)
    assert result.is_valid is True
    assert result.highest_severity is None
    assert result.checked == 5


def test_issues_at_filters_by_exact_severity() -> None:
    result = ValidationResult(issues=[_issue(Severity.WARNING, "w"), _issue(Severity.ERROR, "e")])
    assert [i.code for i in result.issues_at(Severity.WARNING)] == ["w"]


def test_merge_concatenates_and_sums() -> None:
    a = ValidationResult(issues=[_issue(Severity.WARNING)], checked=1)
    b = ValidationResult(issues=[_issue(Severity.ERROR)], checked=2)
    merged = a.merge(b)
    assert merged.checked == 3
    assert merged.is_valid is False
    assert len(merged.issues) == 2


def test_blank_issue_code_rejected() -> None:
    with pytest.raises(ValueError, match="code must not be empty"):
        ValidationIssue(code=" ", message="m")


def test_result_serialises() -> None:
    result = ValidationResult(issues=[_issue(Severity.ERROR)])
    payload = result.to_dict()
    assert payload["is_valid"] is False
    assert payload["issues"][0]["severity"] == "ERROR"


def test_quality_composite_is_weighted_mean() -> None:
    result = QualityResult(
        measurements=[
            QualityMeasurement(dimension="completeness", score=0.8, weight=2.0),
            QualityMeasurement(dimension="accuracy", score=0.5, weight=1.0),
        ]
    )
    assert result.composite_score == pytest.approx(0.7)


def test_quality_composite_zero_when_no_weight() -> None:
    result = QualityResult(measurements=[QualityMeasurement(dimension="d", score=0.9, weight=0.0)])
    assert result.composite_score == 0.0


def test_quality_composite_zero_when_empty() -> None:
    assert QualityResult().composite_score == 0.0


def test_quality_measurement_lookup() -> None:
    result = QualityResult(measurements=[QualityMeasurement(dimension="d", score=0.5)])
    assert result.measurement("d") is not None
    assert result.measurement("absent") is None


@pytest.mark.parametrize("score", [-0.1, 1.1])
def test_quality_score_out_of_range_rejected(score: float) -> None:
    with pytest.raises(ValueError, match="within"):
        QualityMeasurement(dimension="d", score=score)


def test_quality_negative_weight_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        QualityMeasurement(dimension="d", score=0.5, weight=-1.0)


def test_quality_result_serialises() -> None:
    result = QualityResult(measurements=[QualityMeasurement(dimension="d", score=0.5)])
    payload = result.to_dict()
    assert payload["composite_score"] == 0.5
    assert payload["measurements"][0]["dimension"] == "d"
