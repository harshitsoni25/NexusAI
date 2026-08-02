"""Tests for the rule outcome model."""

from __future__ import annotations

from nexusai.domain.model.assessment import Severity
from nexusai.domain.model.rules import RuleOutcome


def test_passed_outcome_has_no_issue() -> None:
    outcome = RuleOutcome(rule="r", passed=True)
    assert outcome.as_issue() is None


def test_failed_outcome_becomes_issue() -> None:
    outcome = RuleOutcome(
        rule="price-range",
        passed=False,
        severity=Severity.WARNING,
        message="too high",
        location="price",
    )
    issue = outcome.as_issue()
    assert issue is not None
    assert issue.code == "price-range"
    assert issue.severity is Severity.WARNING
    assert issue.location == "price"


def test_failed_outcome_uses_default_message() -> None:
    issue = RuleOutcome(rule="r", passed=False).as_issue()
    assert issue is not None
    assert "failed" in issue.message


def test_outcome_serialises() -> None:
    payload = RuleOutcome(rule="r", passed=False, severity=Severity.ERROR).to_dict()
    assert payload == {
        "rule": "r",
        "passed": False,
        "severity": "ERROR",
        "message": "",
        "location": None,
    }
