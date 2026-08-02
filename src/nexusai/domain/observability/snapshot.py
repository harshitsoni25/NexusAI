"""The metrics snapshot: a stable, serialisable summary of a job or run.

A snapshot is the boundary between live collection and everything that consumes
observability after the fact -- the ``stats`` command, report generation,
historical comparison. It aggregates the metrics recorded during a run, a resource
summary, an error summary and the execution timeline into one immutable value, so
a report generator reads a snapshot rather than querying live collectors, and a
comparison next week reads a stored snapshot rather than a vanished registry.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime

from nexusai.domain.observability.resources import ResourceSummary
from nexusai.domain.observability.timeline import Timeline


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricsSnapshot:
    """An immutable summary of one job or run's observability data.

    Attributes:
        job_id: The job this snapshot describes, when applicable.
        generated_at: When the snapshot was assembled.
        metrics: The registry snapshot (counters, gauges, histograms).
        resources: A resource-usage summary, when sampled.
        errors: Error counts by category.
        timeline: The execution timeline.
    """

    job_id: str | None = None
    generated_at: datetime | None = None
    metrics: Mapping[str, object] = field(default_factory=dict)
    resources: ResourceSummary | None = None
    errors: Mapping[str, float] = field(default_factory=dict)
    timeline: Timeline | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {
            "job_id": self.job_id,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "metrics": dict(self.metrics),
            "resources": self.resources.to_dict() if self.resources else None,
            "errors": dict(self.errors),
            "timeline": self.timeline.to_dict() if self.timeline else None,
        }
