"""Pure observability contracts: metrics, timeline, resources, and health.

This package holds the vocabulary of observability -- metric types and units, the
operation-outcome taxonomy, catalog entries, timeline events, resource samples
and health results -- as pure values with no I/O and no vendor. The layers above
record, sample and emit; the domain only defines what those things mean.
"""

from __future__ import annotations

from nexusai.domain.observability.health import (
    HealthCheck,
    HealthReport,
    HealthStatus,
    RuntimeSignal,
)
from nexusai.domain.observability.metrics import (
    MetricDefinition,
    MetricType,
    MetricUnit,
    Outcome,
    is_valid_metric_name,
)
from nexusai.domain.observability.resources import (
    ResourceSample,
    ResourceSummary,
    summarise,
)
from nexusai.domain.observability.snapshot import MetricsSnapshot
from nexusai.domain.observability.timeline import (
    Timeline,
    TimelineEvent,
    TimelineEventType,
)

__all__ = [
    "HealthCheck",
    "HealthReport",
    "HealthStatus",
    "MetricDefinition",
    "MetricType",
    "MetricUnit",
    "MetricsSnapshot",
    "Outcome",
    "ResourceSample",
    "ResourceSummary",
    "RuntimeSignal",
    "Timeline",
    "TimelineEvent",
    "TimelineEventType",
    "is_valid_metric_name",
    "summarise",
]
