"""Models for site analysis and strategy recommendation.

Analysis answers "what is observably true about this target?"; recommendation
answers "given that, which retrieval strategy should we use?". The models keep the
two separate on purpose: an :class:`AnalysisResult` is a set of observed
characteristics with evidence and confidence, carrying no opinion about strategy,
and a :class:`StrategyRecommendation` is the opinion, derived from the analysis by
a distinct component. Detection that is uncertain is reported as uncertain --
confidence is first-class -- rather than dressed up as fact.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Characteristic(Enum):
    """An observable trait of a target the analyzer looks for."""

    STATIC_HTML = "static-html"
    JS_RENDERING = "js-rendering"
    PAGINATION = "pagination"
    OFFSET_PAGINATION = "offset-pagination"
    CURSOR_PAGINATION = "cursor-pagination"
    INFINITE_SCROLL = "infinite-scroll"
    LOAD_MORE = "load-more"
    LAZY_LOADING = "lazy-loading"
    TABLES = "tables"
    CARD_LIST = "card-list"
    STRUCTURED_METADATA = "structured-metadata"
    JSON_LD = "json-ld"
    REST_ENDPOINT = "rest-endpoint"
    GRAPHQL_ENDPOINT = "graphql-endpoint"
    DOWNLOADABLE = "downloadable"
    SITEMAP = "sitemap"
    ROBOTS_TXT = "robots-txt"


class Confidence(Enum):
    """How sure a detection is. Ordered, so a caller can set a threshold."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def rank(self) -> int:
        """A numeric rank where a higher number is greater confidence."""
        return {"low": 0, "medium": 1, "high": 2}[self.value]


class RetrievalStrategy(Enum):
    """A retrieval approach the recommender can propose."""

    HTTP = "http"
    BROWSER = "browser"
    API = "api"
    HYBRID = "hybrid"


@dataclass(frozen=True, slots=True, kw_only=True)
class Observation:
    """One detected characteristic with the evidence behind it.

    Attributes:
        characteristic: What was detected.
        confidence: How sure the detection is.
        evidence: A short, human-readable description of what supports it.
    """

    characteristic: Characteristic
    confidence: Confidence
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "characteristic": self.characteristic.value,
            "confidence": self.confidence.value,
            "evidence": self.evidence,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisResult:
    """The structured outcome of analysing a target.

    Attributes:
        target: The URL analysed.
        observations: The detected characteristics with their evidence.
        warnings: Caveats about the analysis.
        limitations: What the analyzer could not or did not determine.
    """

    target: str
    observations: Sequence[Observation] = field(default_factory=tuple)
    warnings: Sequence[str] = field(default_factory=tuple)
    limitations: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "observations", tuple(self.observations))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "limitations", tuple(self.limitations))

    def has(self, characteristic: Characteristic) -> bool:
        """Whether ``characteristic`` was observed at all."""
        return any(o.characteristic is characteristic for o in self.observations)

    def confidence_of(self, characteristic: Characteristic) -> Confidence | None:
        """Return the confidence of an observation, or ``None`` if not observed."""
        for observation in self.observations:
            if observation.characteristic is characteristic:
                return observation.confidence
        return None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "target": self.target,
            "observations": [o.to_dict() for o in self.observations],
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class StrategyRecommendation:
    """A recommended retrieval strategy derived from an analysis.

    Attributes:
        strategy: The recommended approach.
        confidence: How sure the recommendation is.
        rationale: Why this strategy was chosen.
        alternatives: Other viable strategies, best first.
        warnings: Caveats about the recommendation.
        overridden: Whether configuration or an adapter overrode the analysis.
    """

    strategy: RetrievalStrategy
    confidence: Confidence
    rationale: str = ""
    alternatives: Sequence[RetrievalStrategy] = field(default_factory=tuple)
    warnings: Sequence[str] = field(default_factory=tuple)
    overridden: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "alternatives", tuple(self.alternatives))
        object.__setattr__(self, "warnings", tuple(self.warnings))

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "strategy": self.strategy.value,
            "confidence": self.confidence.value,
            "rationale": self.rationale,
            "alternatives": [s.value for s in self.alternatives],
            "warnings": list(self.warnings),
            "overridden": self.overridden,
        }
