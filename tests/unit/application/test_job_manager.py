"""Tests for the job manager."""

from __future__ import annotations

import pytest

from application_builders import MemoryJobStore
from nexusai.application.jobs.manager import JobManager
from nexusai.domain.errors.exceptions import NexusAIError
from nexusai.domain.model.job import JobState
from nexusai.domain.policy.job_state_machine import InvalidTransitionError
from nexusai.testing import FrozenClock, SequentialIdGenerator


@pytest.fixture
def manager() -> JobManager:
    return JobManager(MemoryJobStore(), clock=FrozenClock(), ids=SequentialIdGenerator())


class TestJobManager:
    def test_create_persists_a_created_job(self, manager: JobManager) -> None:
        job = manager.create("https://x")
        assert job.state is JobState.CREATED
        assert manager.get(job.job_id) is not None

    def test_transition_to_running_sets_started_at(self, manager: JobManager) -> None:
        job = manager.create("https://x")
        running = manager.transition(job, JobState.RUNNING)
        assert running.started_at is not None

    def test_transition_to_terminal_sets_finished_at(self, manager: JobManager) -> None:
        job = manager.transition(manager.create("https://x"), JobState.RUNNING)
        done = manager.transition(job, JobState.COMPLETED)
        assert done.finished_at is not None

    def test_illegal_transition_is_blocked(self, manager: JobManager) -> None:
        job = manager.transition(manager.create("https://x"), JobState.RUNNING)
        done = manager.transition(job, JobState.COMPLETED)
        with pytest.raises(InvalidTransitionError):
            manager.transition(done, JobState.RUNNING)

    def test_record_failure_moves_to_failed_with_summary(self, manager: JobManager) -> None:
        job = manager.transition(manager.create("https://x"), JobState.RUNNING)
        failed = manager.record_failure(job, "boom")
        assert failed.state is JobState.FAILED
        assert failed.error_summary == "boom"

    def test_associations_are_persisted(self, manager: JobManager) -> None:
        job = manager.create("https://x")
        job = manager.associate_dataset(job, "ds", 2)
        job = manager.add_export(job, "e1")
        job = manager.add_report(job, "r1")
        assert job.dataset_ref == "ds"
        assert job.export_refs == ("e1",)
        assert job.report_refs == ("r1",)

    def test_require_raises_for_unknown_job(self, manager: JobManager) -> None:
        with pytest.raises(NexusAIError):
            manager.require("nope")
