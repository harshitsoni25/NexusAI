"""Pure quality-scoring policy: weighted composite and letter grade.

Turning a set of dimension scores into a single grade is a judgement, and like
every judgement in the framework it lives in policy where it can be read, tuned
and tested in isolation. The scorer is pure: given the same measurements and the
same configuration it always returns the same grade, with no clock or state.

Both halves are configurable and transparent. The composite is a weighted mean of
the dimension scores, using each measurement's own weight, so a project can make
completeness count for more than timeliness simply by weighting it. The grade
bands are an explicit, ordered mapping from score thresholds to letters, so
"why a B?" is answered by reading the bands rather than tracing code.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from nexusai.domain.model.assessment import QualityMeasurement, QualityResult
from nexusai.domain.model.quality import QualityGrade

_DEFAULT_BANDS: tuple[tuple[float, QualityGrade], ...] = (
    (0.90, QualityGrade.A),
    (0.80, QualityGrade.B),
    (0.70, QualityGrade.C),
    (0.60, QualityGrade.D),
)


@dataclass(frozen=True, slots=True)
class QualityScorer:
    """Computes a composite score and a letter grade from measurements.

    Args:
        bands: Ordered ``(threshold, grade)`` pairs, highest threshold first. A
            score at or above a threshold earns that grade; a score below every
            threshold earns the fallback. Defaults to the conventional
            ninety/eighty/seventy/sixty bands.
        fallback: The grade for a score below the lowest band.
    """

    bands: Sequence[tuple[float, QualityGrade]] = field(default=_DEFAULT_BANDS)
    fallback: QualityGrade = QualityGrade.F

    def __post_init__(self) -> None:
        ordered = tuple(sorted(self.bands, key=lambda band: band[0], reverse=True))
        object.__setattr__(self, "bands", ordered)

    def composite(self, measurements: Sequence[QualityMeasurement]) -> float:
        """Return the weight-weighted mean of the measurement scores.

        Returns ``0.0`` when there are no measurements or their weights sum to
        zero, so an unscored dataset grades as failing rather than dividing by
        zero.
        """
        total_weight = sum(measurement.weight for measurement in measurements)
        if total_weight <= 0.0:
            return 0.0
        weighted = sum(measurement.score * measurement.weight for measurement in measurements)
        return weighted / total_weight

    def grade_for(self, score: float) -> QualityGrade:
        """Return the letter grade for a composite ``score``."""
        for threshold, grade in self.bands:
            if score >= threshold:
                return grade
        return self.fallback

    def score(
        self, measurements: Sequence[QualityMeasurement]
    ) -> tuple[QualityResult, QualityGrade]:
        """Return the quality result and its grade for ``measurements``."""
        result = QualityResult(measurements=tuple(measurements))
        return result, self.grade_for(result.composite_score)
