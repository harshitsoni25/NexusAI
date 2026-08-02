"""A presentation-independent view of a job's status.

The CLI, a future API and a log line all need to describe where a job is, and
none of them should reach into the job model and format it themselves. This model
is the shared answer: a flat, serialisable snapshot carrying state, stage,
progress and result references, with no Rich or CLI type anywhere near it, so any
presentation surface can render it its own way.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True, kw_only=True)
class JobStatus:
    """A flat, renderer-agnostic snapshot of a job's progress.

    Attributes:
        job_id: The job's identity.
        state: The job's state, as a string.
        current_stage: The stage in progress or last completed.
        completed_stages: How many stages have finished.
        total_stages: How many stages the workflow has, when known.
        elapsed_seconds: Wall-clock time since the job started, when running.
        dataset_ref: The dataset produced, if any.
        checkpoint_ref: The latest checkpoint, if any.
        warnings: Short warning messages.
        error_summary: The failure description, if the job failed.
    """

    job_id: str
    state: str
    current_stage: str | None = None
    completed_stages: int = 0
    total_stages: int = 0
    elapsed_seconds: float | None = None
    dataset_ref: str | None = None
    checkpoint_ref: str | None = None
    warnings: tuple[str, ...] = ()
    error_summary: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", tuple(self.warnings))

    @property
    def progress(self) -> float:
        """The fraction of stages completed, in ``[0, 1]``."""
        if self.total_stages <= 0:
            return 0.0
        return min(1.0, self.completed_stages / self.total_stages)

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "job_id": self.job_id,
            "state": self.state,
            "current_stage": self.current_stage,
            "completed_stages": self.completed_stages,
            "total_stages": self.total_stages,
            "progress": self.progress,
            "elapsed_seconds": self.elapsed_seconds,
            "dataset_ref": self.dataset_ref,
            "checkpoint_ref": self.checkpoint_ref,
            "warnings": list(self.warnings),
            "error_summary": self.error_summary,
        }
