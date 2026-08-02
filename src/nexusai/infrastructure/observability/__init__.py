"""Logging, metrics and correlation adapters."""

from __future__ import annotations

from nexusai.infrastructure.observability.catalog import CATALOG
from nexusai.infrastructure.observability.correlation import (
    bind_log_context,
    correlation_scope,
    current_correlation_id,
    current_log_context,
)
from nexusai.infrastructure.observability.logging import LoguruLogger, configure_logging
from nexusai.infrastructure.observability.metrics import InMemoryMetricsSink, NullMetricsSink
from nexusai.infrastructure.observability.registry import (
    MetricError,
    MetricsRegistry,
    catalog_from,
)
from nexusai.infrastructure.observability.resources import ResourceSampler

__all__ = [
    "CATALOG",
    "InMemoryMetricsSink",
    "LoguruLogger",
    "MetricError",
    "MetricsRegistry",
    "NullMetricsSink",
    "ResourceSampler",
    "bind_log_context",
    "catalog_from",
    "configure_logging",
    "correlation_scope",
    "current_correlation_id",
    "current_log_context",
]
