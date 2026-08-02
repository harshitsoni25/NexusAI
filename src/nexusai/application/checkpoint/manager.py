"""Checkpoint creation and safe resume.

The checkpoint manager writes checkpoints during a run and, on resume, loads the
latest one, proves its integrity, and checks it is compatible with the current
world before letting the workflow continue. It is the guardrail around resume:
the orchestrator will happily restart after any stage, so the manager's job is to
ensure it only does so from a checkpoint that is genuinely safe to trust.

Resume is conservative by construction. A checkpoint that fails its integrity
hash, or that came from an incompatible workflow or schema version, is refused
outright rather than resumed from -- repeating work is recoverable, resuming onto
corrupt or mismatched state may not be.
"""

from __future__ import annotations

from dataclasses import dataclass

from nexusai.__about__ import __version__
from nexusai.domain.errors.exceptions import NexusAIError
from nexusai.domain.model.checkpoint import (
    Checkpoint,
    CheckpointIntegrityError,
    validate_checkpoint,
)
from nexusai.domain.policy.resume_compatibility import (
    ResumeContext,
    assess_compatibility,
)
from nexusai.domain.ports.application import CheckpointStore
from nexusai.domain.ports.observability import Clock, IdGenerator


class ResumeError(NexusAIError):
    """A resume was refused: no checkpoint, failed integrity, or incompatibility."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ResumePlan:
    """The result of preparing a resume: where to restart and any warnings."""

    checkpoint: Checkpoint
    restart_after: str
    warnings: tuple[str, ...] = ()


class CheckpointManager:
    """Writes checkpoints and prepares safe resumes."""

    def __init__(
        self,
        store: CheckpointStore,
        *,
        clock: Clock,
        ids: IdGenerator,
        schema_version: int,
    ) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids
        self._schema_version = schema_version

    def write(
        self,
        *,
        job_id: str,
        workflow_version: str,
        completed_stage: str,
        next_stage: str | None,
        configuration_ref: str | None = None,
        dataset_ref: str | None = None,
        dataset_version: int | None = None,
    ) -> Checkpoint:
        """Create and persist a checkpoint for a completed stage."""
        checkpoint = Checkpoint(
            checkpoint_id=self._ids.new(),
            job_id=job_id,
            workflow_version=workflow_version,
            completed_stage=completed_stage,
            next_stage=next_stage,
            dataset_ref=dataset_ref,
            dataset_version=dataset_version,
            configuration_ref=configuration_ref,
            framework_version=__version__,
            schema_version=self._schema_version,
            created_at=self._clock.now(),
        )
        self._store.save(checkpoint)
        return checkpoint

    def prepare_resume(
        self,
        job_id: str,
        *,
        current_workflow_version: str,
        current_configuration_ref: str | None,
    ) -> ResumePlan:
        """Load, verify and compatibility-check the latest checkpoint for a job.

        Raises:
            ResumeError: If there is no checkpoint, its integrity cannot be
                established, or it is incompatible with the current world.
        """
        checkpoint = self._store.latest(job_id)
        if checkpoint is None:
            raise ResumeError("No checkpoint to resume from", job_id=job_id)

        try:
            validate_checkpoint(checkpoint)
        except CheckpointIntegrityError as error:
            raise ResumeError(
                "Checkpoint integrity could not be established", job_id=job_id
            ) from error

        report = assess_compatibility(
            checkpoint_workflow_version=checkpoint.workflow_version,
            checkpoint_framework_version=checkpoint.framework_version,
            checkpoint_configuration_ref=checkpoint.configuration_ref,
            checkpoint_schema_version=checkpoint.schema_version,
            current=ResumeContext(
                workflow_version=current_workflow_version,
                framework_version=__version__,
                configuration_ref=current_configuration_ref,
                schema_version=self._schema_version,
            ),
        )
        if not report.resumable:
            raise ResumeError(
                "Checkpoint is incompatible with the current configuration",
                job_id=job_id,
                blocking="; ".join(report.blocking()),
            )
        return ResumePlan(
            checkpoint=checkpoint,
            restart_after=checkpoint.completed_stage,
            warnings=tuple(report.warning_details()),
        )
