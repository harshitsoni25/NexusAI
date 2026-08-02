"""Models for visual validation of rendered pages.

Visual validation compares a screenshot captured this run against a stored
baseline and reports how much they differ. The models are pure values: a status
ordered by severity, and a comparison result carrying the measured difference
ratio, the threshold it was judged against, and references to the baseline,
current and difference artefacts. Deciding the ratio, and producing the diff
image, is infrastructure (it reads image bytes); the meaning of the result lives
here.

A pixel difference is evidence of *visual* change, not automatically of meaningful
content change -- the two are separate dimensions, and this model deliberately
carries only the visual one.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VisualStatus(Enum):
    """The outcome of a visual comparison, ordered by severity."""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"

    @property
    def rank(self) -> int:
        """A numeric rank where a higher number is worse."""
        return {"pass": 0, "warning": 1, "fail": 2}[self.value]


@dataclass(frozen=True, slots=True, kw_only=True)
class VisualComparison:
    """The result of comparing a current screenshot against a baseline.

    Attributes:
        difference_ratio: The fraction of the image that differs, in ``[0, 1]``.
        warning_threshold: At or above this ratio the result warns.
        fail_threshold: At or above this ratio the result fails.
        status: The severity the ratio earned against the thresholds.
        baseline_ref: A reference to the baseline screenshot artefact.
        current_ref: A reference to the current screenshot artefact.
        diff_ref: A reference to the difference artefact, when produced.
        comparable: Whether the two images could be compared at all (same size).
    """

    difference_ratio: float
    warning_threshold: float
    fail_threshold: float
    status: VisualStatus
    baseline_ref: str | None = None
    current_ref: str | None = None
    diff_ref: str | None = None
    comparable: bool = True

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {
            "difference_ratio": self.difference_ratio,
            "warning_threshold": self.warning_threshold,
            "fail_threshold": self.fail_threshold,
            "status": self.status.value,
            "baseline_ref": self.baseline_ref,
            "current_ref": self.current_ref,
            "diff_ref": self.diff_ref,
            "comparable": self.comparable,
        }


def classify_difference(
    ratio: float, *, warning_threshold: float, fail_threshold: float
) -> VisualStatus:
    """Classify a difference ratio against the configured thresholds."""
    if ratio >= fail_threshold:
        return VisualStatus.FAIL
    if ratio >= warning_threshold:
        return VisualStatus.WARNING
    return VisualStatus.PASS
