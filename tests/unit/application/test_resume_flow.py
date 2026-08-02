"""Tests for the resume use case over a real checkpoint store."""

from __future__ import annotations

import pytest

from application_builders import make_dataset, make_document, make_extraction
from nexusai.application.checkpoint.manager import CheckpointManager, ResumeError
from nexusai.application.downstream import DatasetPersistenceService
from nexusai.application.jobs.manager import JobManager
from nexusai.application.usecases.scrape import ResumeJobUseCase, StartScrapeUseCase
from nexusai.application.usecases.workflow_factory import ScrapeCollaborators
from nexusai.domain.model.job import JobState
from nexusai.infrastructure.persistence import (
    SqlAlchemyCheckpointStore,
    SqlAlchemyDatasetVersionStore,
    SqlAlchemyJobStore,
    create_session_factory,
    create_sqlite_engine,
    initialise_schema,
)
from nexusai.infrastructure.preflight import parse_robots
from nexusai.testing import FrozenClock, RecordingLogger, SequentialIdGenerator


@pytest.fixture
def factory():  # type: ignore[no-untyped-def]
    engine = create_sqlite_engine()
    initialise_schema(engine)
    return create_session_factory(engine)


def _collaborators(factory) -> ScrapeCollaborators:  # type: ignore[no-untyped-def]
    persistence = DatasetPersistenceService(SqlAlchemyDatasetVersionStore(factory))
    return ScrapeCollaborators(
        preflight=lambda url: parse_robots("User-agent: *\nAllow: /", target=url),
        retriever=lambda ctx: [make_document()],
        extractor=lambda docs: [make_extraction()],
        processor=lambda exts: make_dataset(count=1),
        persist=lambda ds, did, run: persistence.persist(ds, did, run_id=run),
        export=lambda ds, fmt, dest: None,  # type: ignore[arg-type,return-value]
        report=lambda ds, fmt, dest: None,  # type: ignore[arg-type,return-value]
        dataset_id="catalog",
        export_formats=(),
        report_formats=(),
    )


class TestResume:
    def test_resume_with_no_checkpoint_raises(self, factory) -> None:  # type: ignore[no-untyped-def]
        jobs = JobManager(
            SqlAlchemyJobStore(factory), clock=FrozenClock(), ids=SequentialIdGenerator()
        )
        checkpoints = CheckpointManager(
            SqlAlchemyCheckpointStore(factory),
            clock=FrozenClock(),
            ids=SequentialIdGenerator(),
            schema_version=1,
        )
        job = jobs.create("https://x")
        use_case = ResumeJobUseCase(jobs=jobs, checkpoints=checkpoints, logger=RecordingLogger())
        with pytest.raises(ResumeError):
            use_case.execute(job.job_id, _collaborators(factory), correlation_id="c")

    def test_resume_after_run_completes_idempotently(self, factory) -> None:  # type: ignore[no-untyped-def]
        jobs = JobManager(
            SqlAlchemyJobStore(factory), clock=FrozenClock(), ids=SequentialIdGenerator()
        )
        checkpoints = CheckpointManager(
            SqlAlchemyCheckpointStore(factory),
            clock=FrozenClock(),
            ids=SequentialIdGenerator(),
            schema_version=1,
        )
        start = StartScrapeUseCase(
            jobs=jobs,
            checkpoints=checkpoints,
            ids=SequentialIdGenerator(),
            logger=RecordingLogger(),
        )
        outcome = start.execute("https://x/", _collaborators(factory), correlation_id="c")
        assert outcome.job.state is JobState.COMPLETED
        # A checkpoint exists and is resumable; resuming re-runs from the boundary.
        plan = checkpoints.prepare_resume(
            outcome.job.job_id, current_workflow_version="1", current_configuration_ref=None
        )
        assert plan.restart_after in {"process", "persist"}


class TestResumeExecution:
    def test_paused_job_resumes_to_completion(self, factory) -> None:  # type: ignore[no-untyped-def]
        jobs = JobManager(
            SqlAlchemyJobStore(factory), clock=FrozenClock(), ids=SequentialIdGenerator()
        )
        checkpoints = CheckpointManager(
            SqlAlchemyCheckpointStore(factory),
            clock=FrozenClock(),
            ids=SequentialIdGenerator(),
            schema_version=1,
        )
        # A job that ran partway and paused, with a valid checkpoint after "process".
        job = jobs.create("https://x/")
        job = jobs.transition(job, JobState.RUNNING)
        checkpoints.write(
            job_id=job.job_id,
            workflow_version="1",
            completed_stage="process",
            next_stage="validate",
        )
        jobs.transition(job, JobState.PAUSED)

        outcome = ResumeJobUseCase(
            jobs=jobs, checkpoints=checkpoints, logger=RecordingLogger()
        ).execute(job.job_id, _collaborators(factory), correlation_id="c")

        assert outcome.job.state is JobState.COMPLETED
        # Stages up to and including the checkpoint boundary were skipped on resume.
        skipped = {o.name for o in outcome.result.outcomes if o.status.value == "skipped"}
        assert "process" in skipped

    def test_resume_from_incompatible_checkpoint_is_refused(self, factory) -> None:  # type: ignore[no-untyped-def]
        jobs = JobManager(
            SqlAlchemyJobStore(factory), clock=FrozenClock(), ids=SequentialIdGenerator()
        )
        checkpoints = CheckpointManager(
            SqlAlchemyCheckpointStore(factory),
            clock=FrozenClock(),
            ids=SequentialIdGenerator(),
            schema_version=1,
        )
        job = jobs.create("https://x/")
        job = jobs.transition(job, JobState.RUNNING)
        # Checkpoint written under a different workflow version.
        checkpoints.write(
            job_id=job.job_id,
            workflow_version="99",
            completed_stage="process",
            next_stage="validate",
        )
        jobs.transition(job, JobState.PAUSED)

        with pytest.raises(ResumeError):
            ResumeJobUseCase(jobs=jobs, checkpoints=checkpoints, logger=RecordingLogger()).execute(
                job.job_id, _collaborators(factory), correlation_id="c"
            )
