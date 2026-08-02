"""The outcome of evaluating a single business or validation rule.

The rule engine runs many rules over a record and needs a uniform result to
aggregate. A :class:`RuleOutcome` is that result: whether the rule held, how
serious a failure is, and enough identifying detail to trace it back. Rules
themselves are behaviour and live behind a port; this is only the shape of what
they return.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nexusai.domain.model.assessment import Severity, ValidationIssue


@dataclass(frozen=True, slots=True, kw_only=True)
class RuleOutcome:
    """The result of evaluating one rule against one record.

    Attributes:
        rule: The name of the rule that produced this outcome.
        passed: Whether the rule held.
        severity: How serious a failure is; ignored when the rule passed.
        message: A human-readable description of a failure.
        location: The field or record location the rule concerns, when relevant.
    """

    rule: str
    passed: bool
    severity: Severity = Severity.ERROR
    message: str = ""
    location: str | None = None

    def as_issue(self) -> ValidationIssue | None:
        """Return a validation issue for a failed rule, or ``None`` if it passed.

        This is the bridge from the rule engine's outcomes into the shared
        validation vocabulary, so a rule failure aggregates alongside structural
        findings in one :class:`ValidationResult`.
        """
        if self.passed:
            return None
        return ValidationIssue(
            code=self.rule,
            message=self.message or f"rule {self.rule!r} failed",
            severity=self.severity,
            location=self.location,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "rule": self.rule,
            "passed": self.passed,
            "severity": self.severity.name,
            "message": self.message,
            "location": self.location,
        }
