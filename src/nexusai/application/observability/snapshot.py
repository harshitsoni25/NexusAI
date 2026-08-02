"""Assembles a metrics snapshot from live collectors.

The builder is the one place that reaches into the live registry, resource
samples and timeline recorder and freezes them into an immutable
:class:`MetricsSnapshot`. Everything downstream -- the ``stats`` command, report
integration, historical comparison -- consumes the frozen snapshot, so no consumer
depends on the shape or lifetime of the live collectors.
"""

from __future__ import annotations

from nexusai.application.observability.timeline import TimelineRecorder
from nexusai.domain.observability.resources import (
    ResourceSample,
    ResourceSummary,
    summarise,
)
from nexusai.domain.observability.snapshot import MetricsSnapshot
from nexusai.domain.ports.observability import Clock, MetricSink


class SnapshotBuilder:
    """Freezes live observability collectors into an immutable snapshot."""

    def __init__(self, registry: MetricSink, *, clock: Clock) -> None:
        self._registry = registry
        self._clock = clock

    def build(
        self,
        *,
        job_id: str | None = None,
        resource_start: ResourceSample | None = None,
        resource_end: ResourceSample | None = None,
        timeline: TimelineRecorder | None = None,
    ) -> MetricsSnapshot:
        """Assemble a snapshot, computing a resource summary if samples are given."""
        metrics = self._registry.snapshot()
        resources: ResourceSummary | None = None
        if resource_start is not None and resource_end is not None:
            resources = summarise(resource_start, resource_end)
        errors = self._registry.counter_by_dimension("nexusai.error", "category")
        return MetricsSnapshot(
            job_id=job_id,
            generated_at=self._clock.now(),
            metrics=metrics,
            resources=resources,
            errors=errors,
            timeline=timeline.timeline() if timeline is not None else None,
        )


def snapshot_to_performance(snapshot: MetricsSnapshot) -> dict[str, float]:
    """Flatten a snapshot into the performance figures a report section holds.

    This is the one-way bridge from observability to reporting: it produces a flat
    map of named numbers -- error totals by category, resource usage, histogram
    means -- that :meth:`ReportAssembler.assemble` accepts as its ``performance``
    argument. Observability depends on nothing in reporting; reporting consumes
    this dict. Only numeric, bounded figures cross the boundary, never payloads.
    """
    performance: dict[str, float] = {}
    for category, count in snapshot.errors.items():
        performance[f"errors.{category}"] = count
    if snapshot.resources is not None:
        performance["cpu_seconds"] = snapshot.resources.cpu_seconds_used
        performance["wall_seconds"] = snapshot.resources.wall_seconds
        performance["peak_rss_bytes"] = float(snapshot.resources.peak_rss_bytes)
    metrics = snapshot.metrics
    counters = metrics.get("counters", []) if isinstance(metrics, dict) else []
    if isinstance(counters, list):
        for counter in counters:
            if isinstance(counter, dict) and not counter.get("dimensions"):
                performance[str(counter["name"])] = float(counter["value"])
    histograms = metrics.get("histograms", []) if isinstance(metrics, dict) else []
    if isinstance(histograms, list):
        for histogram in histograms:
            if isinstance(histogram, dict) and histogram.get("mean") is not None:
                performance[f"{histogram['name']}.mean"] = float(histogram["mean"])
    return performance
