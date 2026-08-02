"""A storage-independent report model.

Reporting renders a stable model, never ORM rows or a live dataset. That model is
this: a :class:`Report` composed of sections -- run and dataset summaries,
validation and quality and change results, provenance, artefacts, errors and
performance. Every renderer (HTML, JSON, CSV, PDF) consumes the same
:class:`Report`, so the four outputs agree by construction and none of them
recalculates a Phase 5 result -- they present what the model already holds.

The model is assembled by the application layer from a processed dataset; it
copies the validation, quality and change results across rather than deriving
them, which is what keeps reporting free of processing logic.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from nexusai.shared.types import JsonValue


@dataclass(frozen=True, slots=True, kw_only=True)
class RunSummary:
    """High-level facts about the run that produced the dataset."""

    run_id: str | None = None
    framework_version: str = ""
    rule_version: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "run_id": self.run_id,
            "framework_version": self.framework_version,
            "rule_version": self.rule_version,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetSummary:
    """Counts describing the dataset as a whole."""

    dataset_id: str = ""
    version: int = 0
    record_count: int = 0
    field_count: int = 0
    source_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "record_count": self.record_count,
            "field_count": self.field_count,
            "source_count": self.source_count,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidationSummarySection:
    """The dataset's validation outcome, as counts and a status."""

    status: str = "PASS"
    passing_records: int = 0
    failing_records: int = 0
    warning_records: int = 0
    issues: Sequence[Mapping[str, JsonValue]] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "issues", tuple(dict(issue) for issue in self.issues))

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "status": self.status,
            "passing_records": self.passing_records,
            "failing_records": self.failing_records,
            "warning_records": self.warning_records,
            "issues": [dict(issue) for issue in self.issues],
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class QualitySummarySection:
    """The dataset's quality scores and grade."""

    grade: str | None = None
    composite_score: float = 0.0
    dimensions: Sequence[Mapping[str, JsonValue]] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "dimensions", tuple(dict(dim) for dim in self.dimensions))

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "grade": self.grade,
            "composite_score": self.composite_score,
            "dimensions": [dict(dim) for dim in self.dimensions],
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangeSummarySection:
    """The change outcome relative to the previous dataset version."""

    added: int = 0
    removed: int = 0
    modified: int = 0
    detectors: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "detectors", tuple(self.detectors))

    @property
    def total(self) -> int:
        """The total number of changed records."""
        return self.added + self.removed + self.modified

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "added": self.added,
            "removed": self.removed,
            "modified": self.modified,
            "total": self.total,
            "detectors": list(self.detectors),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ProvenanceEntry:
    """One source's contribution to the dataset, for the provenance section."""

    uri: str
    method: str
    retrieved_at: datetime | None = None
    content_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "uri": self.uri,
            "method": self.method,
            "retrieved_at": self.retrieved_at.isoformat() if self.retrieved_at else None,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportArtifact:
    """A reference to an artefact associated with the run."""

    artifact_type: str
    locator: str
    media_type: str
    size_bytes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "artifact_type": self.artifact_type,
            "locator": self.locator,
            "media_type": self.media_type,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class PerformanceSection:
    """Operation timings already recorded elsewhere, surfaced for the report."""

    metrics: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metrics", dict(self.metrics))

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {"metrics": dict(self.metrics)}


@dataclass(frozen=True, slots=True, kw_only=True)
class RenderingSection:
    """Browser-rendering evidence: visual comparison, network and screenshots.

    Populated only for browser-retrieved datasets; it surfaces the visual-diff
    verdict, a network-activity summary and the count of lifecycle screenshots. It
    carries results computed elsewhere -- the report does not run a comparison.
    """

    rendered: bool = False
    visual_status: str | None = None
    visual_difference_ratio: float | None = None
    visual_comparable: bool | None = None
    staged_screenshot_count: int = 0
    network: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "network", dict(self.network))

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "rendered": self.rendered,
            "visual_status": self.visual_status,
            "visual_difference_ratio": self.visual_difference_ratio,
            "visual_comparable": self.visual_comparable,
            "staged_screenshot_count": self.staged_screenshot_count,
            "network": dict(self.network),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class Report:
    """The complete, storage-independent report model.

    Every renderer consumes this. It is assembled once from a processed dataset
    and its context, and copies Phase 5 results across without recomputing them.
    """

    generated_at: datetime
    framework_version: str = ""
    run: RunSummary = field(default_factory=RunSummary)
    dataset: DatasetSummary = field(default_factory=DatasetSummary)
    validation: ValidationSummarySection = field(default_factory=ValidationSummarySection)
    quality: QualitySummarySection = field(default_factory=QualitySummarySection)
    change: ChangeSummarySection = field(default_factory=ChangeSummarySection)
    provenance: Sequence[ProvenanceEntry] = field(default_factory=tuple)
    artifacts: Sequence[ReportArtifact] = field(default_factory=tuple)
    performance: PerformanceSection = field(default_factory=PerformanceSection)
    rendering: RenderingSection | None = None
    errors: Sequence[str] = field(default_factory=tuple)
    warnings: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "provenance", tuple(self.provenance))
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(self, "errors", tuple(self.errors))
        object.__setattr__(self, "warnings", tuple(self.warnings))

    def to_dict(self) -> dict[str, Any]:
        """Return a fully serialisable representation of the report."""
        return {
            "generated_at": self.generated_at.isoformat(),
            "framework_version": self.framework_version,
            "run": self.run.to_dict(),
            "dataset": self.dataset.to_dict(),
            "validation": self.validation.to_dict(),
            "quality": self.quality.to_dict(),
            "change": self.change.to_dict(),
            "provenance": [entry.to_dict() for entry in self.provenance],
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "performance": self.performance.to_dict(),
            "rendering": self.rendering.to_dict() if self.rendering else None,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }
