"""Scraping endpoints: submit and resume scrapes as background jobs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from nexusai_pro_api.dependencies import GatewayDep, JobRunnerDep
from nexusai_pro_api.schemas.jobs import SubmissionStatus
from nexusai_pro_api.schemas.scraping import ResumeRequest, ScrapeAccepted, ScrapeRequest

router = APIRouter(prefix="/scrape", tags=["Scraping"])


def _dataset_id(explicit: str | None, target: str) -> str:
    if explicit:
        return explicit
    return "ds-" + uuid.uuid5(uuid.NAMESPACE_URL, target).hex[:12]


@router.post(
    "",
    response_model=ScrapeAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a scrape (runs in the background)",
)
def start_scrape(body: ScrapeRequest, runner: JobRunnerDep, _: GatewayDep) -> ScrapeAccepted:
    """Accept a scrape for background execution and return a submission handle.

    The engine runs synchronously, so the work is executed off the event loop; poll
    the returned status URL (and the jobs endpoints) for progress.
    """
    submission_id = uuid.uuid4().hex
    dataset_id = _dataset_id(body.dataset_id, body.target)
    record = runner.submit_scrape(
        submission_id,
        body.target,
        dataset_id=dataset_id,
        export_formats=tuple(body.export_formats),
        report_formats=tuple(body.report_formats),
    )
    return ScrapeAccepted(
        submission_id=record.submission_id,
        state=record.state,
        target=record.target,
        dataset_id=record.dataset_id,
        job_id=record.job_id,
        status_url=f"/api/v1/scrape/{record.submission_id}",
    )


@router.get("/{submission_id}", response_model=SubmissionStatus, summary="Submission status")
def submission_status(submission_id: str, runner: JobRunnerDep) -> SubmissionStatus:
    """Report progress of a previously accepted scrape submission."""
    from nexusai_pro_api.errors import not_found

    record = runner.get_submission(submission_id)
    if record is None:
        raise not_found("submission", submission_id)
    return SubmissionStatus(
        submission_id=record.submission_id,
        state=record.state,
        target=record.target,
        dataset_id=record.dataset_id,
        job_id=record.job_id,
        error=record.error,
    )


@router.post(
    "/{job_id}/resume",
    response_model=ScrapeAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Resume a job from its checkpoint",
)
def resume_scrape(job_id: str, body: ResumeRequest, gateway: GatewayDep) -> ScrapeAccepted:
    """Resume a previously started job from its last checkpoint (synchronous)."""
    job = gateway.resume_scrape(
        job_id,
        target=body.target,
        dataset_id=body.dataset_id,
        export_formats=tuple(body.export_formats),
        report_formats=tuple(body.report_formats),
    )
    return ScrapeAccepted(
        submission_id=job_id,
        state="finished",
        target=body.target,
        dataset_id=body.dataset_id,
        job_id=job.job_id,
        status_url=f"/api/v1/jobs/{job.job_id}",
    )
