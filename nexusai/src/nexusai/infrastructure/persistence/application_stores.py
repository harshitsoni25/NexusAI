"""SQLAlchemy stores for jobs, checkpoints and schedules.

These repositories implement the application-state ports over the metadata store,
returning domain value objects and never ORM rows. Jobs and schedules are
upserted by primary key so a state change replaces the prior row; checkpoints are
append-only and the latest row for a job is the current one, so a failed write can
never overwrite the last valid checkpoint -- it simply adds a row, and the
integrity check on load rejects any that is unsound.

The rich, variable parts of each aggregate travel as JSON in a ``payload`` column
and are rehydrated through the models' own constructors, which keeps the schema
stable while the value objects evolve.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from nexusai.domain.model.checkpoint import Checkpoint
from nexusai.domain.model.job import Job, JobState, JobType
from nexusai.domain.model.schedule import (
    OverlapPolicy,
    Schedule,
    ScheduleExpression,
    ScheduleKind,
)
from nexusai.infrastructure.persistence.application_schema import (
    CheckpointRow,
    JobRow,
    ScheduleRow,
)


class SqlAlchemyJobStore:
    """Persists and retrieves jobs."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, job: Job) -> None:
        """Insert or replace a job by ``job_id``."""
        with self._session_factory() as session:
            row = session.get(JobRow, job.job_id)
            if row is None:
                row = JobRow(job_id=job.job_id)
                session.add(row)
            _apply_job(row, job)
            session.commit()

    def get(self, job_id: str) -> Job | None:
        """Return the job with ``job_id``, or ``None``."""
        with self._session_factory() as session:
            row = session.get(JobRow, job_id)
            return _job_from_row(row) if row is not None else None

    def list(self, *, limit: int = 100) -> Sequence[Job]:
        """Return recent jobs, newest first by creation time."""
        with self._session_factory() as session:
            rows = session.scalars(
                select(JobRow).order_by(JobRow.created_at.desc()).limit(limit)
            ).all()
            return [_job_from_row(row) for row in rows]


class SqlAlchemyCheckpointStore:
    """Persists checkpoints append-only and returns the latest for a job."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, checkpoint: Checkpoint) -> None:
        """Append a checkpoint. Never overwrites the last valid one."""
        with self._session_factory() as session:
            session.add(
                CheckpointRow(
                    checkpoint_id=checkpoint.checkpoint_id,
                    job_id=checkpoint.job_id,
                    created_at=checkpoint.created_at,
                    payload=json.dumps(checkpoint.to_dict(), default=str),
                )
            )
            session.commit()

    def latest(self, job_id: str) -> Checkpoint | None:
        """Return the most recently written checkpoint for a job."""
        with self._session_factory() as session:
            row = session.scalar(
                select(CheckpointRow)
                .where(CheckpointRow.job_id == job_id)
                .order_by(CheckpointRow.id.desc())
                .limit(1)
            )
            return _checkpoint_from_row(row) if row is not None else None


class SqlAlchemyScheduleStore:
    """Persists and retrieves schedules."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, schedule: Schedule) -> None:
        """Insert or replace a schedule by ``schedule_id``."""
        with self._session_factory() as session:
            row = session.get(ScheduleRow, schedule.schedule_id)
            if row is None:
                row = ScheduleRow(schedule_id=schedule.schedule_id)
                session.add(row)
            row.name = schedule.name
            row.target = schedule.target
            row.enabled = schedule.enabled
            row.next_run = schedule.next_run
            row.last_run = schedule.last_run
            row.interval_seconds = schedule.expression.interval_seconds
            row.payload = json.dumps(schedule.to_dict(), default=str)
            session.commit()

    def get(self, schedule_id: str) -> Schedule | None:
        """Return the schedule with ``schedule_id``, or ``None``."""
        with self._session_factory() as session:
            row = session.get(ScheduleRow, schedule_id)
            return _schedule_from_row(row) if row is not None else None

    def list(self) -> Sequence[Schedule]:
        """Return every schedule."""
        with self._session_factory() as session:
            rows = session.scalars(select(ScheduleRow)).all()
            return [_schedule_from_row(row) for row in rows]

    def delete(self, schedule_id: str) -> None:
        """Remove a schedule. Absent identity is a no-op."""
        with self._session_factory() as session:
            row = session.get(ScheduleRow, schedule_id)
            if row is not None:
                session.delete(row)
                session.commit()


def _apply_job(row: JobRow, job: Job) -> None:
    row.target = job.target
    row.job_type = job.job_type.value
    row.state = job.state.value
    row.created_at = job.created_at
    row.started_at = job.started_at
    row.finished_at = job.finished_at
    row.current_stage = job.current_stage
    row.configuration_ref = job.configuration_ref
    row.workflow_version = job.workflow_version
    row.dataset_ref = job.dataset_ref
    row.dataset_version = job.dataset_version
    row.checkpoint_ref = job.checkpoint_ref
    row.error_summary = job.error_summary
    row.payload = json.dumps(
        {
            "report_refs": list(job.report_refs),
            "export_refs": list(job.export_refs),
            "resume_metadata": dict(job.resume_metadata),
            "attributes": dict(job.attributes),
        },
        default=str,
    )


def _job_from_row(row: JobRow) -> Job:
    payload = json.loads(row.payload)
    return Job(
        job_id=row.job_id,
        target=row.target,
        job_type=JobType(row.job_type),
        state=JobState(row.state),
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
        current_stage=row.current_stage,
        configuration_ref=row.configuration_ref,
        workflow_version=row.workflow_version,
        dataset_ref=row.dataset_ref,
        dataset_version=row.dataset_version,
        checkpoint_ref=row.checkpoint_ref,
        error_summary=row.error_summary,
        report_refs=tuple(payload.get("report_refs", [])),
        export_refs=tuple(payload.get("export_refs", [])),
        resume_metadata=payload.get("resume_metadata", {}),
        attributes=payload.get("attributes", {}),
    )


def _checkpoint_from_row(row: CheckpointRow) -> Checkpoint:
    data = json.loads(row.payload)
    return Checkpoint(
        checkpoint_id=data["checkpoint_id"],
        job_id=data["job_id"],
        workflow_version=data["workflow_version"],
        completed_stage=data["completed_stage"],
        next_stage=data.get("next_stage"),
        dataset_ref=data.get("dataset_ref"),
        dataset_version=data.get("dataset_version"),
        pagination_state=data.get("pagination_state", {}),
        configuration_ref=data.get("configuration_ref"),
        plugin_versions=data.get("plugin_versions", {}),
        framework_version=data.get("framework_version", ""),
        schema_version=data.get("schema_version", 0),
        created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
        version=data.get("version", 1),
        integrity_hash=data.get("integrity_hash", ""),
    )


def _schedule_from_row(row: ScheduleRow) -> Schedule:
    data = json.loads(row.payload)
    expr = data["expression"]
    return Schedule(
        schedule_id=row.schedule_id,
        name=row.name,
        target=row.target,
        expression=ScheduleExpression(
            kind=ScheduleKind(expr["kind"]),
            at=datetime.fromisoformat(expr["at"]) if expr.get("at") else None,
            interval_seconds=expr.get("interval_seconds"),
            cron=expr.get("cron"),
        ),
        enabled=row.enabled,
        overlap_policy=OverlapPolicy(data.get("overlap_policy", "skip")),
        configuration_ref=data.get("configuration_ref"),
        created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
        last_run=row.last_run,
        next_run=row.next_run,
        last_result=data.get("last_result"),
    )
