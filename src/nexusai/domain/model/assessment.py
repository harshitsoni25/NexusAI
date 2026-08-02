"""Generic result containers for validation and quality assessment.

These are reusable *shapes*, not rules. A ``ValidationResult`` records whether a
check passed and what it found; a ``QualityResult`` records a score and the
measurements behind it. The rules that produce them -- execution validation
thresholds, data-quality specifications -- are pure domain policy introduced with
the engines that own them.

Keeping the containers generic and separate from the rules is what lets Phase 6's
execution validation and Phase 7's data-quality assessment both report through a
common vocabulary, and lets a plugin-supplied validator return the same shape as
a built-in one.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from nexusai.shared.types import JsonMapping


class Severity(Enum):
    """How serious a finding is.

    Ordered, so that a caller can ask for "the worst severity present" or filter
    to "error and above" without hardcoding the ranking at each call site.
    """

    INFO = 10
    WARNING = 20
    ERROR = 30
    CRITICAL = 40

    def __lt__(self, other: Severity) -> bool:
        return self.value < other.value

    def __le__(self, other: Severity) -> bool:
        return self.value <= other.value


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidationIssue:
    """A single thing a validator found wrong or noteworthy.

    Attributes:
        code: A stable, machine-readable identifier for the kind of issue, such
            as ``missing-required-field``. Stable so that reports can aggregate
            and alerts can match on it without depending on the human message.
        message: A human-readable description.
        severity: How serious the issue is.
        location: Where the issue was found -- a field name, a selector, a record
            identifier -- when applicable.
        context: Structured detail supporting the finding.
    """

    code: str
    message: str
    severity: Severity = Severity.ERROR
    location: str | None = None
    context: JsonMapping = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("ValidationIssue.code must not be empty")
        object.__setattr__(self, "context", dict(self.context))

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.name,
            "location": self.location,
            "context": dict(self.context),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidationResult:
    """The outcome of a validation: a verdict and the issues behind it.

    The verdict is derived, not stored independently, so it can never contradict
    the issues. A result is valid exactly when it carries no issue at or above
    ``error`` severity -- warnings and information do not, on their own, mean
    failure.
    """

    issues: Sequence[ValidationIssue] = field(default_factory=tuple)
    checked: int = 1
    metadata: JsonMapping = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "issues", tuple(self.issues))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def is_valid(self) -> bool:
        """Whether nothing at error severity or above was found."""
        return not any(issue.severity >= Severity.ERROR for issue in self.issues)

    @property
    def highest_severity(self) -> Severity | None:
        """The most serious severity present, or ``None`` when there are none."""
        return max((issue.severity for issue in self.issues), default=None)

    def issues_at(self, severity: Severity) -> Sequence[ValidationIssue]:
        """Return the issues at exactly ``severity``."""
        return tuple(issue for issue in self.issues if issue.severity is severity)

    def merge(self, other: ValidationResult) -> ValidationResult:
        """Combine two results, concatenating issues and summing counts.

        Useful when several validators contribute to one verdict: the merged
        result is valid only if both components were.
        """
        return ValidationResult(
            issues=(*self.issues, *other.issues),
            checked=self.checked + other.checked,
            metadata={**self.metadata, **other.metadata},
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "is_valid": self.is_valid,
            "checked": self.checked,
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def passing(cls, *, checked: int = 1) -> ValidationResult:
        """Return a result with no issues."""
        return cls(issues=(), checked=checked)


@dataclass(frozen=True, slots=True, kw_only=True)
class QualityMeasurement:
    """A single scored dimension of quality.

    Attributes:
        dimension: What was measured -- "completeness", "accuracy". A free-form
            label, because the set of dimensions is configuration, not a fixed
            enumeration the core owns.
        score: The dimension's score, normalised to the range 0.0 to 1.0.
        weight: How much this dimension contributes to the composite, relative to
            the others.
        detail: Supporting numbers, such as counts behind the score.
    """

    dimension: str
    score: float
    weight: float = 1.0
    detail: JsonMapping = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be within [0.0, 1.0], got {self.score}")
        if self.weight < 0.0:
            raise ValueError(f"weight must be non-negative, got {self.weight}")
        object.__setattr__(self, "detail", dict(self.detail))

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "dimension": self.dimension,
            "score": self.score,
            "weight": self.weight,
            "detail": dict(self.detail),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class QualityResult:
    """A composite quality score and the measurements it was computed from.

    The composite is the weighted mean of the measurements, computed on access
    rather than stored, so it cannot drift out of step with the measurements. The
    breakdown is always retained alongside it, because a single number hides
    which dimension collapsed.
    """

    measurements: Sequence[QualityMeasurement] = field(default_factory=tuple)
    metadata: JsonMapping = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "measurements", tuple(self.measurements))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def composite_score(self) -> float:
        """The weighted mean of the measurements, or 0.0 when there are none."""
        total_weight = sum(item.weight for item in self.measurements)
        if total_weight == 0.0:
            return 0.0
        weighted = sum(item.score * item.weight for item in self.measurements)
        return weighted / total_weight

    def measurement(self, dimension: str) -> QualityMeasurement | None:
        """Return the measurement for ``dimension``, or ``None`` if absent."""
        for item in self.measurements:
            if item.dimension == dimension:
                return item
        return None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "composite_score": self.composite_score,
            "measurements": [item.to_dict() for item in self.measurements],
            "metadata": dict(self.metadata),
        }
