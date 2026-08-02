"""Application-side observability: context, instrumentation, recorders, snapshots.

This package coordinates observation without owning behaviour. It propagates an
execution-safe context, provides timing instrumentation and failure isolation,
records metrics from results the framework already produced, assembles the
timeline, freezes a metrics snapshot, and assesses operational health. It records
and reads; it never re-runs work.
"""

from __future__ import annotations

from nexusai.application.observability.context import (
    ObservabilityContext,
    current_context,
    observability_scope,
)
from nexusai.application.observability.health import HealthThresholds, assess_health
from nexusai.application.observability.instrumentation import timed, timer
from nexusai.application.observability.safety import safely
from nexusai.application.observability.snapshot import SnapshotBuilder, snapshot_to_performance
from nexusai.application.observability.timeline import TimelineRecorder

__all__ = [
    "HealthThresholds",
    "ObservabilityContext",
    "SnapshotBuilder",
    "TimelineRecorder",
    "assess_health",
    "current_context",
    "observability_scope",
    "safely",
    "snapshot_to_performance",
    "timed",
    "timer",
]
