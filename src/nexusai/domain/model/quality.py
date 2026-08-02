"""Quality dimensions and grades for data-quality assurance.

Structural validation asks "is this record well-formed?"; quality assurance asks
"is this dataset trustworthy?" -- a different and coarser question, answered
across six dimensions rather than per field. This module names those dimensions
and the letter grade a composite score earns, both as closed enumerations so a
report can rely on them, while the *weights and thresholds* that turn scores into
a grade stay configurable in policy.
"""

from __future__ import annotations

from enum import Enum


class QualityDimension(Enum):
    """The dimensions along which dataset quality is assessed.

    A closed set because these six are the framework's quality vocabulary; a
    project needing another dimension registers a custom assessor with its own
    free-form label rather than extending this enum.
    """

    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    UNIQUENESS = "uniqueness"
    INTEGRITY = "integrity"
    TIMELINESS = "timeliness"


class QualityGrade(Enum):
    """A letter grade summarising a composite quality score.

    The ordering matters -- ``A`` is better than ``F`` -- so the members are
    comparable, letting a caller express a minimum acceptable grade as a simple
    comparison.
    """

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"

    @property
    def rank(self) -> int:
        """A numeric rank where a higher number is a better grade."""
        order = {"F": 0, "D": 1, "C": 2, "B": 3, "A": 4}
        return order[self.value]

    def __lt__(self, other: QualityGrade) -> bool:
        """Order grades so that ``F < D < C < B < A``."""
        return self.rank < other.rank

    def __le__(self, other: QualityGrade) -> bool:
        """Order grades so that a grade is less than or equal to a better one."""
        return self.rank <= other.rank
