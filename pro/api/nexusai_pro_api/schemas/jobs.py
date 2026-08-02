"""Response models for jobs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class JobSummary(BaseModel):
    job_id: str
    target: str | None = None
    state: str | None = Field(
        default=None, description="Engine job state (e.g. completed, failed, running)."
    )
    dataset_id: str | None = None

    @classmethod
    def from_engine(cls, job: Any) -> JobSummary:
        return cls(
            job_id=getattr(job, "job_id", ""),
            target=getattr(job, "target", None),
            state=_state_of(job),
            dataset_id=getattr(job, "dataset_id", None),
        )


class JobDetail(JobSummary):
    detail: dict[str, Any] = Field(
        default_factory=dict, description="Engine-provided job detail, best-effort."
    )

    @classmethod
    def from_engine(cls, job: Any) -> JobDetail:
        base = JobSummary.from_engine(job)
        to_dict = getattr(job, "to_dict", None)
        detail = to_dict() if callable(to_dict) else {}
        return cls(**base.model_dump(), detail=detail)


class JobList(BaseModel):
    jobs: list[JobSummary]
    count: int


class SubmissionStatus(BaseModel):
    submission_id: str
    state: str
    target: str
    dataset_id: str
    job_id: str | None = None
    error: str | None = None


def _state_of(job: Any) -> str | None:
    state = getattr(job, "state", None)
    if state is None:
        return None
    return getattr(state, "value", str(state))
