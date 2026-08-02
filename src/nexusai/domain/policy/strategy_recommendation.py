"""Pure policy mapping observed characteristics to a retrieval strategy.

Detection and recommendation are separated (the analyzer observes; this decides),
and this half is pure so the mapping from "what the page looks like" to "how to
fetch it" can be read and tested in isolation. The reasoning is explicit: a
public API observation favours the API strategy; a hard dependency on JavaScript
rendering or infinite scroll favours the browser; static HTML favours plain HTTP;
and a page that is static but paginates behind script is a hybrid.

Configuration or a site adapter may override the result, but the override is
recorded as such alongside the analysis-derived recommendation, so a run can
always show both what was suggested and what was chosen.
"""

from __future__ import annotations

from nexusai.domain.model.analysis import (
    AnalysisResult,
    Characteristic,
    Confidence,
    RetrievalStrategy,
    StrategyRecommendation,
)


def recommend_strategy(analysis: AnalysisResult) -> StrategyRecommendation:
    """Recommend a retrieval strategy from an analysis result."""
    has = analysis.has

    if has(Characteristic.REST_ENDPOINT) or has(Characteristic.GRAPHQL_ENDPOINT):
        return StrategyRecommendation(
            strategy=RetrievalStrategy.API,
            confidence=Confidence.HIGH,
            rationale="a public data endpoint was observed",
            alternatives=(RetrievalStrategy.HTTP, RetrievalStrategy.BROWSER),
        )

    needs_browser = (
        has(Characteristic.JS_RENDERING)
        or has(Characteristic.INFINITE_SCROLL)
        or has(Characteristic.LOAD_MORE)
    )
    if needs_browser:
        alternatives = (RetrievalStrategy.HYBRID,)
        if has(Characteristic.STATIC_HTML):
            return StrategyRecommendation(
                strategy=RetrievalStrategy.HYBRID,
                confidence=Confidence.MEDIUM,
                rationale=(
                    "static content is present but dynamic loading was observed; "
                    "a hybrid approach covers both"
                ),
                alternatives=(RetrievalStrategy.BROWSER, RetrievalStrategy.HTTP),
            )
        return StrategyRecommendation(
            strategy=RetrievalStrategy.BROWSER,
            confidence=Confidence.MEDIUM,
            rationale="the page depends on client-side rendering or interaction",
            alternatives=alternatives,
        )

    if has(Characteristic.STATIC_HTML):
        return StrategyRecommendation(
            strategy=RetrievalStrategy.HTTP,
            confidence=Confidence.HIGH,
            rationale="content is present in the static HTML response",
            alternatives=(RetrievalStrategy.BROWSER,),
        )

    return StrategyRecommendation(
        strategy=RetrievalStrategy.HTTP,
        confidence=Confidence.LOW,
        rationale="no strong signal was observed; defaulting to HTTP",
        alternatives=(RetrievalStrategy.BROWSER,),
        warnings=("analysis was inconclusive",),
    )


def apply_override(
    recommendation: StrategyRecommendation, override: RetrievalStrategy
) -> StrategyRecommendation:
    """Return a recommendation reflecting an explicit strategy override."""
    return StrategyRecommendation(
        strategy=override,
        confidence=recommendation.confidence,
        rationale=f"overridden to {override.value} (analysis suggested "
        f"{recommendation.strategy.value})",
        alternatives=(recommendation.strategy,),
        warnings=recommendation.warnings,
        overridden=True,
    )
