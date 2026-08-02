"""The framework's metric catalog: every production metric, documented.

Each entry fixes a metric's name, type, unit, allowed dimensions and meaning, so
there are no undocumented metrics and no ambiguous counters. The naming standard
is consistent -- ``nexusai.<area>.<measurement>`` -- and the distinctions that
matter (attempted vs successful vs failed vs skipped vs retried) are separate
metrics or a bounded ``outcome`` dimension, never guesswork.

Dimensions are bounded categories only: an outcome, a stage name, an export
format, an error category, an HTTP status class. No dimension is a URL, an
exception message or a raw value.
"""

from __future__ import annotations

from nexusai.domain.observability.metrics import (
    MetricDefinition,
    MetricType,
    MetricUnit,
)

_C = MetricType.COUNTER
_G = MetricType.GAUGE
_T = MetricType.TIMER
_H = MetricType.HISTOGRAM


def _d(
    name: str, mtype: MetricType, unit: MetricUnit, desc: str, dims: tuple[str, ...] = ()
) -> MetricDefinition:
    return MetricDefinition(
        name=name, metric_type=mtype, unit=unit, description=desc, dimensions=dims
    )


CATALOG: tuple[MetricDefinition, ...] = (
    # Jobs
    _d("nexusai.job.created", _C, MetricUnit.COUNT, "Jobs created."),
    _d("nexusai.job.started", _C, MetricUnit.COUNT, "Jobs started."),
    _d(
        "nexusai.job.finished",
        _C,
        MetricUnit.COUNT,
        "Jobs finished, by final state.",
        ("state",),
    ),
    _d("nexusai.job.duration", _T, MetricUnit.SECONDS, "Wall-clock job duration."),
    _d("nexusai.job.resume_attempted", _C, MetricUnit.COUNT, "Resume attempts."),
    _d("nexusai.job.resume_outcome", _C, MetricUnit.COUNT, "Resume outcomes.", ("outcome",)),
    # Workflow / stages
    _d("nexusai.workflow.executed", _C, MetricUnit.COUNT, "Workflow executions."),
    _d("nexusai.stage.outcome", _C, MetricUnit.COUNT, "Stage outcomes.", ("stage", "status")),
    _d("nexusai.stage.duration", _T, MetricUnit.SECONDS, "Stage duration.", ("stage",)),
    # Pages
    _d("nexusai.page.outcome", _C, MetricUnit.COUNT, "Page outcomes.", ("outcome",)),
    _d("nexusai.page.records", _H, MetricUnit.RECORDS, "Records per page."),
    # Retrieval
    _d("nexusai.request.attempted", _C, MetricUnit.COUNT, "Requests attempted.", ("provider",)),
    _d(
        "nexusai.request.outcome",
        _C,
        MetricUnit.COUNT,
        "Request outcomes.",
        ("provider", "outcome"),
    ),
    _d(
        "nexusai.request.status_class",
        _C,
        MetricUnit.COUNT,
        "HTTP status classes.",
        ("status_class",),
    ),
    _d("nexusai.request.duration", _T, MetricUnit.SECONDS, "Request duration.", ("provider",)),
    _d("nexusai.request.response_bytes", _H, MetricUnit.BYTES, "Response size."),
    # Retries
    _d("nexusai.retry.attempted", _C, MetricUnit.COUNT, "Retry attempts.", ("category",)),
    _d("nexusai.retry.outcome", _C, MetricUnit.COUNT, "Retry outcomes.", ("outcome",)),
    # Extraction
    _d("nexusai.extraction.documents", _C, MetricUnit.COUNT, "Documents processed."),
    _d("nexusai.extraction.records", _C, MetricUnit.COUNT, "Records extracted."),
    _d(
        "nexusai.extraction.fields",
        _C,
        MetricUnit.COUNT,
        "Field extraction outcomes.",
        ("outcome",),
    ),
    _d("nexusai.extraction.duration", _T, MetricUnit.SECONDS, "Extraction duration."),
    # Validation / DQA
    _d("nexusai.validation.result", _C, MetricUnit.COUNT, "Validation results.", ("result",)),
    _d("nexusai.quality.score", _G, MetricUnit.RATIO, "Overall quality score."),
    _d("nexusai.quality.grade", _C, MetricUnit.COUNT, "Quality grades.", ("grade",)),
    # Persistence
    _d(
        "nexusai.persistence.operation",
        _C,
        MetricUnit.COUNT,
        "Persistence operations.",
        ("operation", "outcome"),
    ),
    _d(
        "nexusai.persistence.duration",
        _T,
        MetricUnit.SECONDS,
        "Persistence op duration.",
        ("operation",),
    ),
    _d("nexusai.persistence.records", _H, MetricUnit.RECORDS, "Records per write."),
    # Export / reporting
    _d(
        "nexusai.export.operation",
        _C,
        MetricUnit.COUNT,
        "Export operations.",
        ("format", "outcome"),
    ),
    _d("nexusai.export.duration", _T, MetricUnit.SECONDS, "Export duration.", ("format",)),
    _d("nexusai.export.bytes", _H, MetricUnit.BYTES, "Export size.", ("format",)),
    _d(
        "nexusai.report.operation",
        _C,
        MetricUnit.COUNT,
        "Report operations.",
        ("format", "outcome"),
    ),
    _d("nexusai.report.duration", _T, MetricUnit.SECONDS, "Report duration.", ("format",)),
    # Concurrency / queues
    _d("nexusai.concurrency.active", _G, MetricUnit.COUNT, "Active concurrent operations."),
    _d("nexusai.concurrency.limit", _G, MetricUnit.COUNT, "Configured concurrency limit."),
    _d("nexusai.concurrency.wait", _T, MetricUnit.SECONDS, "Wait for available capacity."),
    _d("nexusai.queue.depth", _G, MetricUnit.COUNT, "Queue depth."),
    _d("nexusai.queue.capacity", _G, MetricUnit.COUNT, "Queue capacity."),
    _d(
        "nexusai.queue.backpressure",
        _C,
        MetricUnit.COUNT,
        "Backpressure (producer-blocked) events.",
    ),
    # Errors
    _d("nexusai.error", _C, MetricUnit.COUNT, "Errors by category.", ("category",)),
    # Resources
    _d("nexusai.resource.cpu_seconds", _G, MetricUnit.SECONDS, "Process CPU seconds used."),
    _d("nexusai.resource.rss_bytes", _G, MetricUnit.BYTES, "Resident set size."),
)
"""The published metric catalog. Every metric the framework records is here."""
