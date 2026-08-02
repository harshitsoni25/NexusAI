"""The job manager: the one place job state changes.

Every lifecycle operation on a job -- create, start, transition, associate a
result, record a failure, cancel, complete -- goes through this manager, and the
manager routes every state change through the state-machine policy. No other code
mutates a job's state, so "what can happen to a job" is enforced in one place
rather than trusted to callers.

Jobs are persisted through the :class:`JobStore` port, not held only in memory,
so a job survives the process that created it and can be resumed later.
"""

from __future__ import annotations

from dataclasses import replace

from nexusai.domain.errors.exceptions import NexusAIError
from nexusai.domain.model.job import Job, JobState, JobType
from nexusai.domain.policy.job_state_machine import ensure_transition
from nexusai.domain.ports.application import JobStore
from nexusai.domain.ports.observability import Clock, IdGenerator

_FINISHED = frozenset({JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED, JobState.PARTIAL})


class JobManager:
    """Creates jobs and mediates every change to their state."""

    def __init__(self, store: JobStore, *, clock: Clock, ids: IdGenerator) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids

    def create(
        self,
        target: str,
        *,
        job_type: JobType = JobType.SCRAPE,
        configuration_ref: str | None = None,
        workflow_version: str = "1",
    ) -> Job:
        """Create and persist a new job in the ``CREATED`` state."""
        job = Job(
            job_id=self._ids.new(),
            target=target,
            job_type=job_type,
            state=JobState.CREATED,
            created_at=self._clock.now(),
            configuration_ref=configuration_ref,
            workflow_version=workflow_version,
        )
        self._store.save(job)
        return job

    def get(self, job_id: str) -> Job | None:
        """Return the job with ``job_id``, or ``None``."""
        return self._store.get(job_id)

    def list_jobs(self, *, limit: int = 100) -> list[Job]:
        """Return recent jobs, newest first."""
        return list(self._store.list(limit=limit))

    def require(self, job_id: str) -> Job:
        """Return the job with ``job_id``, or raise if absent.

        Raises:
            NexusAIError: If no such job exists.
        """
        job = self._store.get(job_id)
        if job is None:
            raise NexusAIError("No such job", job_id=job_id)
        return job

    def transition(self, job: Job, target: JobState) -> Job:
        """Move a job to ``target`` via the state machine, and persist it.

        Raises:
            InvalidTransitionError: If the transition is not permitted.
        """
        ensure_transition(job.state, target)
        changes: dict[str, object] = {"state": target}
        if target is JobState.RUNNING and job.started_at is None:
            changes["started_at"] = self._clock.now()
        if target in _FINISHED:
            changes["finished_at"] = self._clock.now()
        updated = replace(job, **changes)  # type: ignore[arg-type]
        self._store.save(updated)
        return updated

    def update_stage(self, job: Job, stage: str) -> Job:
        """Record the current stage on a job and persist it."""
        updated = replace(job, current_stage=stage)
        self._store.save(updated)
        return updated

    def associate_dataset(self, job: Job, dataset_ref: str, version: int) -> Job:
        """Record the dataset a job produced."""
        updated = replace(job, dataset_ref=dataset_ref, dataset_version=version)
        self._store.save(updated)
        return updated

    def associate_checkpoint(self, job: Job, checkpoint_ref: str) -> Job:
        """Record a job's latest checkpoint."""
        updated = replace(job, checkpoint_ref=checkpoint_ref)
        self._store.save(updated)
        return updated

    def add_export(self, job: Job, export_ref: str) -> Job:
        """Append an export reference to a job."""
        updated = replace(job, export_refs=(*job.export_refs, export_ref))
        self._store.save(updated)
        return updated

    def add_report(self, job: Job, report_ref: str) -> Job:
        """Append a report reference to a job."""
        updated = replace(job, report_refs=(*job.report_refs, report_ref))
        self._store.save(updated)
        return updated

    def record_failure(self, job: Job, summary: str) -> Job:
        """Move a job to ``FAILED`` and record why."""
        failed = self.transition(job, JobState.FAILED)
        updated = replace(failed, error_summary=summary)
        self._store.save(updated)
        return updated
