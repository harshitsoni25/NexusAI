"""Tests for metric recorders, timeline, snapshot, and health assessment."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from nexusai.application.observability.health import HealthThresholds, assess_health
from nexusai.application.observability.recorders import (
    record_error,
    record_export,
    record_job_finished,
    record_retrieval,
)
from nexusai.application.observability.snapshot import (
    SnapshotBuilder,
    snapshot_to_performance,
)
from nexusai.application.observability.timeline import TimelineRecorder
from nexusai.domain.errors.exceptions import NetworkError, ValidationError
from nexusai.domain.model.job import Job, JobState
from nexusai.domain.model.persistence import ExportManifest, OutcomeStatus
from nexusai.domain.model.retrieval import Document
from nexusai.domain.observability.health import HealthStatus
from nexusai.domain.observability.timeline import TimelineEventType
from nexusai.domain.provenance.source import ArtifactReference
from nexusai.infrastructure.observability.catalog import CATALOG
from nexusai.infrastructure.observability.registry import MetricsRegistry, catalog_from
from nexusai.infrastructure.observability.resources import ResourceSampler
from nexusai.testing import FrozenClock


def _registry() -> MetricsRegistry:
    return MetricsRegistry(catalog_from(CATALOG))


def _now() -> datetime:
    return datetime(2025, 1, 1, tzinfo=UTC)


class TestRecorders:
    def test_record_job_finished_state_and_duration(self) -> None:
        reg = _registry()
        job = Job(
            job_id="j",
            target="t",
            state=JobState.COMPLETED,
            started_at=_now(),
            finished_at=_now() + timedelta(seconds=3),
        )
        record_job_finished(reg, job)
        assert reg.counter_by_dimension("nexusai.job.finished", "state") == {"completed": 1.0}

    def test_non_terminal_job_not_recorded(self) -> None:
        reg = _registry()
        record_job_finished(reg, Job(job_id="j", target="t", state=JobState.RUNNING))
        assert reg.counter_total("nexusai.job.finished") == 0

    def test_record_retrieval_status_class_and_bytes(self) -> None:
        reg = _registry()
        doc = Document(
            url="u",
            content=b"x" * 500,
            status_code=200,
            provider="httpx",
            retrieved_at=_now(),
            media_type="text/html",
        )
        record_retrieval(reg, doc, duration_seconds=0.2)
        assert reg.counter_by_dimension("nexusai.request.status_class", "status_class") == {
            "2xx": 1.0
        }

    def test_record_error_uses_category(self) -> None:
        reg = _registry()
        record_error(reg, NetworkError("down"))
        record_error(reg, ValidationError("bad"))
        record_error(reg, RuntimeError("generic"))
        by_cat = reg.counter_by_dimension("nexusai.error", "category")
        assert by_cat == {"acquisition": 1.0, "validation": 1.0, "internal": 1.0}

    def test_record_export_from_manifest(self) -> None:
        reg = _registry()
        manifest = ExportManifest(
            export_id="e",
            dataset_id="d",
            dataset_version=1,
            export_format="csv",
            artifact=ArtifactReference(locator="f.csv", media_type="text/csv", size_bytes=100),
            record_count=10,
            size_bytes=100,
            content_hash="h",
            created_at=_now(),
            duration_seconds=0.5,
            status=OutcomeStatus.SUCCESS,
        )
        record_export(reg, manifest)
        assert reg.counter_by_dimension("nexusai.export.operation", "format") == {"csv": 1.0}


class TestTimeline:
    def test_records_ordered_events(self) -> None:
        recorder = TimelineRecorder(FrozenClock())
        recorder.record(TimelineEventType.JOB_STARTED, label="j1")
        recorder.record(TimelineEventType.STAGE_COMPLETED, label="retrieve")
        timeline = recorder.timeline()
        assert [e.event_type for e in timeline.events] == [
            TimelineEventType.JOB_STARTED,
            TimelineEventType.STAGE_COMPLETED,
        ]


class TestSnapshot:
    def test_snapshot_aggregates_errors_and_resources(self) -> None:
        reg = _registry()
        record_error(reg, NetworkError("x"))
        record_error(reg, NetworkError("y"))
        sampler = ResourceSampler()
        start, end = sampler.sample(), sampler.sample()
        snapshot = SnapshotBuilder(reg, clock=FrozenClock()).build(
            job_id="j1", resource_start=start, resource_end=end
        )
        assert snapshot.job_id == "j1"
        assert snapshot.errors == {"acquisition": 2.0}
        assert snapshot.resources is not None

    def test_snapshot_to_performance_flattens(self) -> None:
        reg = _registry()
        record_error(reg, NetworkError("x"))
        snapshot = SnapshotBuilder(reg, clock=FrozenClock()).build(job_id="j1")
        performance = snapshot_to_performance(snapshot)
        assert performance["errors.acquisition"] == 1.0


class TestHealth:
    def test_high_failure_rate_fails(self) -> None:
        reg = _registry()
        for _ in range(7):
            reg.increment("nexusai.job.finished", dimensions={"state": "completed"})
        for _ in range(3):
            reg.increment("nexusai.job.finished", dimensions={"state": "failed"})
        report = assess_health(reg)
        assert report.status is HealthStatus.FAIL

    def test_queue_saturation_warns(self) -> None:
        reg = _registry()
        reg.gauge("nexusai.queue.depth", 9)
        reg.gauge("nexusai.queue.capacity", 10)
        report = assess_health(reg)
        signal = next(c for c in report.checks if c.name == "queue_saturation")
        assert signal.status is HealthStatus.WARNING

    def test_thresholds_are_configurable(self) -> None:
        reg = _registry()
        for _ in range(9):
            reg.increment("nexusai.job.finished", dimensions={"state": "completed"})
        reg.increment("nexusai.job.finished", dimensions={"state": "failed"})
        strict = HealthThresholds(failure_rate_warning=0.05, failure_rate_fail=0.08)
        report = assess_health(reg, thresholds=strict)
        assert report.status is HealthStatus.FAIL

    def test_no_activity_passes(self) -> None:
        assert assess_health(_registry()).status is HealthStatus.PASS
