"""The Site Analyzer application service, keeping detection and advice apart.

This service coordinates two deliberately separate steps. First it retrieves the
target through the approved retrieval engine and asks the detectors what is
observably true about the returned markup, producing an :class:`AnalysisResult`
that carries no opinion about strategy. Then, as a distinct call, it maps that
analysis to a :class:`StrategyRecommendation` through the pure recommendation
policy.

The separation is the point of the design: detection reports facts with
confidence, recommendation offers advice, and a caller can take the analysis
without the advice or override the advice while keeping the facts. Retrieval goes
through the engine, so the analyzer never fetches anything the framework would not
otherwise fetch, and performs no bypass.
"""

from __future__ import annotations

from collections.abc import Callable

from nexusai.domain.model.analysis import (
    AnalysisResult,
    RetrievalStrategy,
    StrategyRecommendation,
)
from nexusai.domain.model.retrieval import Document
from nexusai.domain.policy.strategy_recommendation import (
    apply_override,
    recommend_strategy,
)

DocumentFetcher = Callable[[str], Document]
Detector = Callable[[str, bytes], AnalysisResult]


class SiteAnalyzer:
    """Analyses a target's observable characteristics from retrieved markup."""

    def __init__(self, fetch: DocumentFetcher, detect: Detector) -> None:
        self._fetch = fetch
        self._detect = detect

    def analyse(self, target: str) -> AnalysisResult:
        """Retrieve ``target`` and detect its observable characteristics."""
        document = self._fetch(target)
        return self._detect(target, document.content)


class StrategyRecommender:
    """Maps an analysis to a strategy recommendation, honouring overrides."""

    def recommend(
        self, analysis: AnalysisResult, *, override: RetrievalStrategy | None = None
    ) -> StrategyRecommendation:
        """Recommend a strategy for ``analysis``, applying ``override`` if given."""
        recommendation = recommend_strategy(analysis)
        if override is not None:
            return apply_override(recommendation, override)
        return recommendation
