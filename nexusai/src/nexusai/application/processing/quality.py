"""The data-quality assurance engine.

Runs a set of dimension assessors over a dataset, collects their measurements,
and applies the scoring policy to produce a composite score and a letter grade.
Assessment is separated from scoring: the assessors say how each dimension did,
and the pure :class:`QualityScorer` decides what that means overall, so the
weighting and grading can be tuned without touching the assessors.
"""

from __future__ import annotations

from collections.abc import Sequence

from nexusai.domain.model.assessment import QualityResult
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.domain.model.quality import QualityGrade
from nexusai.domain.policy.quality_scoring import QualityScorer
from nexusai.domain.ports.processing import QualityDimensionAssessor


class QualityEngine:
    """Assesses dataset quality across dimensions and grades the result."""

    def __init__(
        self,
        assessors: Sequence[QualityDimensionAssessor],
        *,
        scorer: QualityScorer | None = None,
    ) -> None:
        self._assessors = tuple(assessors)
        self._scorer = scorer or QualityScorer()

    def assess(self, dataset: ProcessedDataset) -> tuple[QualityResult, QualityGrade]:
        """Assess every dimension and return the result and its grade."""
        measurements = [assessor.assess(dataset) for assessor in self._assessors]
        return self._scorer.score(measurements)
