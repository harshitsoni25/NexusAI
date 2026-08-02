"""Models for operational health checks and runtime signals.

Health answers "is the system in a good state to operate?" as a set of checks,
each PASS, WARNING or FAIL with a short diagnostic. Runtime signals are the
lighter-weight, threshold-driven observations a running system surfaces -- a high
retry rate, queue saturation, memory pressure. Both are pure models; deciding a
threshold is breached, or running a check, happens in the layers above.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum


class HealthStatus(Enum):
    """The status of a health check or runtime signal, ordered by severity."""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"

    @property
    def rank(self) -> int:
        """A numeric rank where a higher number is worse."""
        return {"pass": 0, "warning": 1, "fail": 2}[self.value]


@dataclass(frozen=True, slots=True, kw_only=True)
class HealthCheck:
    """The result of one health check.

    Attributes:
        name: A stable identifier for the check.
        status: Whether it passed, warned or failed.
        detail: A short human-readable description.
        remediation: Actionable guidance when not passing.
    """

    name: str
    status: HealthStatus
    detail: str = ""
    remediation: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {
            "name": self.name,
            "status": self.status.value,
            "detail": self.detail,
            "remediation": self.remediation,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class HealthReport:
    """A collection of health checks with an overall verdict."""

    checks: Sequence[HealthCheck]

    @property
    def status(self) -> HealthStatus:
        """The worst status among the checks."""
        worst = HealthStatus.PASS
        for check in self.checks:
            if check.status.rank > worst.rank:
                worst = check.status
        return worst

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {
            "status": self.status.value,
            "checks": [check.to_dict() for check in self.checks],
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeSignal:
    """A threshold-driven observation about a running system.

    Attributes:
        name: What the signal concerns (retry rate, queue saturation).
        status: The severity of the observation.
        value: The observed value.
        threshold: The threshold that was compared against.
        detail: A short description.
    """

    name: str
    status: HealthStatus
    value: float
    threshold: float
    detail: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {
            "name": self.name,
            "status": self.status.value,
            "value": self.value,
            "threshold": self.threshold,
            "detail": self.detail,
        }
