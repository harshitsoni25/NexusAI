"""The analyze-site use case.

Coordinates the Site Analyzer and the strategy recommender, keeping their two
outputs distinct: it returns the analysis (observed characteristics with
confidence) and the recommendation (advised strategy) as separate results, so a
caller sees both what is true and what is advised, and can act on either. The use
case retrieves through the approved engine and performs no bypass.
"""

from __future__ import annotations

from dataclasses import dataclass

from nexusai.application.analysis import SiteAnalyzer, StrategyRecommender
from nexusai.domain.model.analysis import (
    AnalysisResult,
    RetrievalStrategy,
    StrategyRecommendation,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class SiteAnalysis:
    """The combined, but internally separate, analysis and recommendation."""

    analysis: AnalysisResult
    recommendation: StrategyRecommendation

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {
            "analysis": self.analysis.to_dict(),
            "recommendation": self.recommendation.to_dict(),
        }


class AnalyzeSiteUseCase:
    """Analyses a target and recommends a retrieval strategy."""

    def __init__(self, analyzer: SiteAnalyzer, recommender: StrategyRecommender) -> None:
        self._analyzer = analyzer
        self._recommender = recommender

    def execute(self, target: str, *, override: RetrievalStrategy | None = None) -> SiteAnalysis:
        """Return the analysis and strategy recommendation for ``target``."""
        analysis = self._analyzer.analyse(target)
        recommendation = self._recommender.recommend(analysis, override=override)
        return SiteAnalysis(analysis=analysis, recommendation=recommendation)
