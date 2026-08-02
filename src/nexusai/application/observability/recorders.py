"""Metric recorders that read existing results and record, never recompute.

Each recorder takes a value the framework already produced -- a finished job, a
stage outcome, a retrieved document, a processed dataset, an export manifest -- and
records the metrics that follow from it. None of them re-runs retrieval,
extraction, processing, validation or export to obtain a number: the validation
result is read from the dataset the pipeline already assessed, the export size is
read from the manifest the exporter already wrote. Observability consumes; it does
not own behaviour.

Every recorder is fault-isolated by the caller (see ``safely``): a metric that
fails to record must never fail the work it describes.
"""

from __future__ import annotations

from nexusai.application.workflow.orchestrator import WorkflowResult
from nexusai.domain.errors.exceptions import NexusAIError
from nexusai.domain.model.job import Job, JobState
from nexusai.domain.model.persistence import ExportManifest, ReportManifest
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.domain.model.retrieval import Document
from nexusai.domain.model.workflow import StageOutcome, StageStatus
from nexusai.domain.ports.observability import MetricSink

_STATUS_CLASS = {2: "2xx", 3: "3xx", 4: "4xx", 5: "5xx"}


def record_job_finished(registry: MetricSink, job: Job) -> None:
    """Record a job's terminal state and, if timed, its duration."""
    if not job.is_terminal:
        return
    registry.increment("nexusai.job.finished", dimensions={"state": job.state.value})
    if job.started_at is not None and job.finished_at is not None:
        registry.observe(
            "nexusai.job.duration",
            max(0.0, (job.finished_at - job.started_at).total_seconds()),
        )


def record_workflow_result(registry: MetricSink, result: WorkflowResult) -> None:
    """Record the workflow execution and each stage's outcome."""
    registry.increment("nexusai.workflow.executed")
    for outcome in result.outcomes:
        record_stage_outcome(registry, outcome)


def record_stage_outcome(
    registry: MetricSink, outcome: StageOutcome, *, duration_seconds: float | None = None
) -> None:
    """Record one stage's outcome and optional duration."""
    registry.increment(
        "nexusai.stage.outcome",
        dimensions={"stage": outcome.name, "status": outcome.status.value},
    )
    if outcome.status is StageStatus.FAILED:
        registry.increment("nexusai.error", dimensions={"category": "internal"})
    if duration_seconds is not None:
        registry.observe(
            "nexusai.stage.duration", duration_seconds, dimensions={"stage": outcome.name}
        )


def record_retrieval(
    registry: MetricSink,
    document: Document,
    *,
    duration_seconds: float,
    outcome: str = "success",
) -> None:
    """Record a retrieval from a document the provider already returned."""
    provider = document.provider or "unknown"
    registry.increment("nexusai.request.attempted", dimensions={"provider": provider})
    registry.increment(
        "nexusai.request.outcome", dimensions={"provider": provider, "outcome": outcome}
    )
    status_class = _STATUS_CLASS.get(document.status_code // 100, "other")
    registry.increment("nexusai.request.status_class", dimensions={"status_class": status_class})
    registry.observe(
        "nexusai.request.duration", duration_seconds, dimensions={"provider": provider}
    )
    registry.observe("nexusai.request.response_bytes", float(len(document.content)))


def record_dataset(registry: MetricSink, dataset: ProcessedDataset) -> None:
    """Record validation, quality and record metrics from a processed dataset.

    Reads the validation and quality results the processing pipeline already
    produced; it does not re-validate or re-score.
    """
    registry.increment("nexusai.extraction.records", float(len(dataset)))
    result = "pass" if dataset.is_valid else "fail"
    registry.increment("nexusai.validation.result", dimensions={"result": result})
    context = dataset.context
    if context is not None:
        registry.gauge("nexusai.quality.score", context.quality.composite_score)
        registry.increment(
            "nexusai.quality.grade", dimensions={"grade": context.quality_grade.value}
        )


def record_export(registry: MetricSink, manifest: ExportManifest) -> None:
    """Record an export from its manifest."""
    fmt = manifest.export_format
    registry.increment(
        "nexusai.export.operation",
        dimensions={"format": fmt, "outcome": manifest.status.value},
    )
    registry.observe(
        "nexusai.export.duration", manifest.duration_seconds, dimensions={"format": fmt}
    )
    registry.observe("nexusai.export.bytes", float(manifest.size_bytes), dimensions={"format": fmt})


def record_report(
    registry: MetricSink, manifest: ReportManifest, *, duration_seconds: float = 0.0
) -> None:
    """Record a report from its manifest."""
    fmt = manifest.report_format
    registry.increment(
        "nexusai.report.operation",
        dimensions={"format": fmt, "outcome": manifest.status.value},
    )
    if duration_seconds:
        registry.observe("nexusai.report.duration", duration_seconds, dimensions={"format": fmt})


def record_error(registry: MetricSink, error: Exception) -> None:
    """Record an error, classified by the approved exception category."""
    category = error.category.value if isinstance(error, NexusAIError) else "internal"
    registry.increment("nexusai.error", dimensions={"category": category})


def record_resource_gauges(registry: MetricSink, *, cpu_seconds: float, rss_bytes: int) -> None:
    """Record the latest resource readings as gauges."""
    registry.gauge("nexusai.resource.cpu_seconds", cpu_seconds)
    registry.gauge("nexusai.resource.rss_bytes", float(rss_bytes))


def _job_states() -> tuple[str, ...]:
    return tuple(state.value for state in JobState)
