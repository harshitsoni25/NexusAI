"""Jobs endpoints: list and inspect engine jobs."""

from __future__ import annotations

from fastapi import APIRouter, Query

from nexusai_pro_api.dependencies import GatewayDep
from nexusai_pro_api.schemas.jobs import JobDetail, JobList, JobSummary

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=JobList, summary="List jobs")
def list_jobs(gateway: GatewayDep, limit: int = Query(default=50, ge=1, le=1000)) -> JobList:
    """List recent jobs recorded by the engine, newest first."""
    jobs = gateway.list_jobs(limit=limit)
    summaries = [JobSummary.from_engine(job) for job in jobs]
    return JobList(jobs=summaries, count=len(summaries))


@router.get("/{job_id}", response_model=JobDetail, summary="Get a job")
def get_job(job_id: str, gateway: GatewayDep) -> JobDetail:
    """Return the current state and detail of a single job."""
    from nexusai_pro_api.errors import not_found

    job = gateway.get_job(job_id)
    if job is None:
        raise not_found("job", job_id)
    return JobDetail.from_engine(job)
