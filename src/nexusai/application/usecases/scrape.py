"""The scrape and resume use cases.

These are the application's entry points for running a workflow. ``StartScrape``
creates a job, drives it through the orchestrator while mediating every state
change through the job manager, writes checkpoints after the marked stages, and
records the final outcome -- completed, partial, failed or cancelled -- with the
partial-failure policy deciding which. ``ResumeJob`` prepares a safe resume from
the latest valid checkpoint and re-runs the workflow from the restart boundary,
skipping the stages already done.

The use cases coordinate; they do not scrape. Retrieval, extraction, processing,
persistence, export and reporting all reach them through the workflow stages,
which delegate to the engines and services of earlier phases.
"""

from __future__ import annotations

from dataclasses import dataclass

from nexusai.application.checkpoint.manager import CheckpointManager
from nexusai.application.jobs.manager import JobManager
from nexusai.application.runtime.cancellation import CancellationToken
from nexusai.application.runtime.context import ExecutionContext
from nexusai.application.usecases.workflow_factory import (
    ScrapeCollaborators,
    build_scrape_stages,
    standard_scrape_workflow,
)
from nexusai.application.workflow.orchestrator import WorkflowOrchestrator, WorkflowResult
from nexusai.application.workflow.stage import Workspace
from nexusai.domain.model.job import Job, JobState, JobType
from nexusai.domain.ports.observability import IdGenerator, Logger


@dataclass(frozen=True, slots=True, kw_only=True)
class ScrapeOutcome:
    """The result of a scrape or resume: the final job and the workflow result."""

    job: Job
    result: WorkflowResult


class StartScrapeUseCase:
    """Creates a job and runs the standard scraping workflow to completion."""

    def __init__(
        self,
        *,
        jobs: JobManager,
        checkpoints: CheckpointManager,
        ids: IdGenerator,
        logger: Logger,
    ) -> None:
        self._jobs = jobs
        self._checkpoints = checkpoints
        self._ids = ids
        self._logger = logger

    def execute(
        self,
        target: str,
        collaborators: ScrapeCollaborators,
        *,
        correlation_id: str,
        configuration_ref: str | None = None,
        cancellation: CancellationToken | None = None,
    ) -> ScrapeOutcome:
        """Run a scrape of ``target`` and return the final job and result."""
        workflow = standard_scrape_workflow()
        job = self._jobs.create(
            target,
            job_type=JobType.SCRAPE,
            configuration_ref=configuration_ref,
            workflow_version=workflow.version,
        )
        job = self._jobs.transition(job, JobState.RUNNING)

        token = cancellation or CancellationToken()
        context = ExecutionContext(
            job_id=job.job_id,
            correlation_id=correlation_id,
            workflow_version=workflow.version,
            target=target,
            configuration_ref=configuration_ref,
            cancellation=token,
        )
        stages = build_scrape_stages(collaborators)

        def on_checkpoint(stage: str, ctx: ExecutionContext) -> str:
            checkpoint = self._checkpoints.write(
                job_id=job.job_id,
                workflow_version=workflow.version,
                completed_stage=stage,
                next_stage=None,
                configuration_ref=configuration_ref,
                dataset_ref=ctx.dataset_ref,
                dataset_version=ctx.dataset_version,
            )
            return checkpoint.checkpoint_id

        orchestrator = WorkflowOrchestrator(
            workflow, stages, logger=self._logger, on_checkpoint=on_checkpoint
        )
        result = orchestrator.run(context, Workspace())
        job = self._finalise(job, result)
        return ScrapeOutcome(job=job, result=result)

    def _finalise(self, job: Job, result: WorkflowResult) -> Job:
        job = self._jobs.get(job.job_id) or job
        if job.is_terminal:
            return job
        if result.context.dataset_ref is not None:
            job = self._jobs.associate_dataset(
                job, result.context.dataset_ref, result.context.dataset_version or 1
            )
        if result.context.checkpoint_ref is not None:
            job = self._jobs.associate_checkpoint(job, result.context.checkpoint_ref)
        if result.final_state is JobState.FAILED:
            summary = "; ".join(result.warnings) or "workflow failed"
            return self._jobs.record_failure(job, summary)
        return self._jobs.transition(job, result.final_state)


class ResumeJobUseCase:
    """Resumes a paused job from its latest valid checkpoint."""

    def __init__(
        self,
        *,
        jobs: JobManager,
        checkpoints: CheckpointManager,
        logger: Logger,
    ) -> None:
        self._jobs = jobs
        self._checkpoints = checkpoints
        self._logger = logger

    def execute(
        self,
        job_id: str,
        collaborators: ScrapeCollaborators,
        *,
        correlation_id: str,
        cancellation: CancellationToken | None = None,
    ) -> ScrapeOutcome:
        """Resume ``job_id`` from its checkpoint and return the final job/result.

        Raises:
            ResumeError: If the job cannot be safely resumed.
            InvalidTransitionError: If the job is not in a recoverable state.
        """
        job = self._jobs.require(job_id)
        workflow = standard_scrape_workflow()
        plan = self._checkpoints.prepare_resume(
            job_id,
            current_workflow_version=workflow.version,
            current_configuration_ref=job.configuration_ref,
        )
        job = self._jobs.transition(job, JobState.RUNNING)

        token = cancellation or CancellationToken()
        context = ExecutionContext(
            job_id=job.job_id,
            correlation_id=correlation_id,
            workflow_version=workflow.version,
            target=job.target,
            configuration_ref=job.configuration_ref,
            checkpoint_ref=plan.checkpoint.checkpoint_id,
            cancellation=token,
        )
        stages = build_scrape_stages(collaborators)
        orchestrator = WorkflowOrchestrator(workflow, stages, logger=self._logger)
        result = orchestrator.run(context, Workspace(), start_after=plan.restart_after)
        job = self._jobs.get(job.job_id) or job
        if not job.is_terminal:
            if result.final_state is JobState.FAILED:
                job = self._jobs.record_failure(job, "; ".join(result.warnings))
            else:
                job = self._jobs.transition(job, result.final_state)
        return ScrapeOutcome(job=job, result=result)
