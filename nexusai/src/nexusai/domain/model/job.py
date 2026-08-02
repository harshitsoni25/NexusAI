"""The application-level job: one execution of a scraping workflow.

A job is the unit the application layer schedules, runs, checkpoints and resumes.
It is deliberately coarse -- one job is one workflow run against one target -- and
kept separate from the fine-grained concepts of earlier phases: a job is not an
HTTP request, a page or an extracted record, and holds references to datasets and
reports rather than their contents.

The job's :class:`JobState` is the spine of the whole application layer. Every
transition is mediated by the state machine policy, never by direct mutation, so
"which states can follow which" is one auditable table rather than scattered
assignments.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from nexusai.shared.types import JsonValue


class JobState(Enum):
    """The lifecycle state of a job.

    Terminal states (``COMPLETED``, ``FAILED``, ``CANCELLED``) admit no further
    transition. ``PARTIAL`` is terminal-but-successful-enough: the run finished
    with a materially complete result that nonetheless fell short of a clean
    ``COMPLETED``. ``PAUSED`` is the recoverable state a resume starts from.
    """

    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    PARTIAL = "partial"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(Enum):
    """What kind of work a job performs."""

    SCRAPE = "scrape"
    ANALYZE = "analyze"
    EXPORT = "export"
    REPORT = "report"
    VALIDATE = "validate"
    BENCHMARK = "benchmark"


@dataclass(frozen=True, slots=True, kw_only=True)
class Job:
    """One execution of a workflow against a target.

    Frozen: state changes produce a new job through the job manager, never an
    in-place mutation, so a job value is always a consistent snapshot. References
    to heavyweight results (datasets, checkpoints, reports) are held as
    identifiers, not embedded objects.

    Attributes:
        job_id: The stable identity of this job.
        target: The site or URL the job operates on.
        job_type: What the job does.
        state: The current lifecycle state.
        created_at: When the job was created.
        started_at: When execution began, if it has.
        finished_at: When execution ended, if it has.
        current_stage: The workflow stage in progress or last completed.
        configuration_ref: A hash or label identifying the effective configuration.
        workflow_version: The version of the workflow definition used.
        dataset_ref: The persisted dataset this job produced, if any.
        dataset_version: The dataset version, if any.
        checkpoint_ref: The latest checkpoint, if any.
        report_refs: References to reports produced.
        export_refs: References to exports produced.
        error_summary: A short description of the failure, if the job failed.
        resume_metadata: Data needed to resume, such as a restart boundary.
        attributes: Free-form execution metadata.
    """

    job_id: str
    target: str
    job_type: JobType = JobType.SCRAPE
    state: JobState = JobState.CREATED
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    current_stage: str | None = None
    configuration_ref: str | None = None
    workflow_version: str = "1"
    dataset_ref: str | None = None
    dataset_version: int | None = None
    checkpoint_ref: str | None = None
    report_refs: tuple[str, ...] = ()
    export_refs: tuple[str, ...] = ()
    error_summary: str | None = None
    resume_metadata: Mapping[str, JsonValue] = field(default_factory=dict)
    attributes: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "report_refs", tuple(self.report_refs))
        object.__setattr__(self, "export_refs", tuple(self.export_refs))
        object.__setattr__(self, "resume_metadata", dict(self.resume_metadata))
        object.__setattr__(self, "attributes", dict(self.attributes))

    @property
    def is_terminal(self) -> bool:
        """Whether the job has reached a state it cannot leave."""
        return self.state in _TERMINAL_STATES

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "job_id": self.job_id,
            "target": self.target,
            "job_type": self.job_type.value,
            "state": self.state.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "current_stage": self.current_stage,
            "configuration_ref": self.configuration_ref,
            "workflow_version": self.workflow_version,
            "dataset_ref": self.dataset_ref,
            "dataset_version": self.dataset_version,
            "checkpoint_ref": self.checkpoint_ref,
            "report_refs": list(self.report_refs),
            "export_refs": list(self.export_refs),
            "error_summary": self.error_summary,
            "resume_metadata": dict(self.resume_metadata),
            "attributes": dict(self.attributes),
        }


_TERMINAL_STATES: frozenset[JobState] = frozenset(
    {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED, JobState.PARTIAL}
)
