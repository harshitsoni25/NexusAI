"""Read-only use cases: job status, listing, and framework statistics.

These coordinate the read side of the application. ``JobStatusUseCase`` assembles
the presentation-independent :class:`JobStatus` from a persisted job and its
workflow; ``StatisticsUseCase`` rolls up the jobs already recorded into counts by
state. They compute nothing new about the data itself -- they surface what the
job and dataset stores already hold -- and they return domain models, never CLI
types, so any presentation surface can render them.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from nexusai.application.jobs.manager import JobManager
from nexusai.application.usecases.workflow_factory import standard_scrape_workflow
from nexusai.domain.model.job import Job
from nexusai.domain.model.status import JobStatus


class JobStatusUseCase:
    """Assembles a job's presentation-independent status."""

    def __init__(self, jobs: JobManager) -> None:
        self._jobs = jobs

    def execute(self, job_id: str) -> JobStatus:
        """Return the status of ``job_id``.

        Raises:
            NexusAIError: If no such job exists.
        """
        job = self._jobs.require(job_id)
        workflow = standard_scrape_workflow()
        stage_names = workflow.stage_names()
        completed = (
            stage_names.index(job.current_stage) + 1 if job.current_stage in stage_names else 0
        )
        elapsed = None
        if job.started_at is not None and job.finished_at is not None:
            elapsed = (job.finished_at - job.started_at).total_seconds()
        return JobStatus(
            job_id=job.job_id,
            state=job.state.value,
            current_stage=job.current_stage,
            completed_stages=completed,
            total_stages=len(stage_names),
            elapsed_seconds=elapsed,
            dataset_ref=job.dataset_ref,
            checkpoint_ref=job.checkpoint_ref,
            error_summary=job.error_summary,
        )


class ListJobsUseCase:
    """Lists recent jobs."""

    def __init__(self, jobs: JobManager) -> None:
        self._jobs = jobs

    def execute(self, *, limit: int = 50) -> Sequence[Job]:
        """Return recent jobs, newest first."""
        return self._jobs.list_jobs(limit=limit)


@dataclass(frozen=True, slots=True, kw_only=True)
class Statistics:
    """A roll-up of job outcomes."""

    total_jobs: int
    by_state: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {"total_jobs": self.total_jobs, "by_state": dict(self.by_state)}


class StatisticsUseCase:
    """Rolls up recorded jobs into counts by state."""

    def __init__(self, jobs: JobManager) -> None:
        self._jobs = jobs

    def execute(self) -> Statistics:
        """Return statistics over all recorded jobs."""
        jobs = self._jobs.list_jobs(limit=10_000)
        by_state: dict[str, int] = {}
        for job in jobs:
            by_state[job.state.value] = by_state.get(job.state.value, 0) + 1
        return Statistics(total_jobs=len(jobs), by_state=by_state)
