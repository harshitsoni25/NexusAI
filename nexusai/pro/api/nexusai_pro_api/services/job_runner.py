"""Runs synchronous engine scrapes as background jobs.

The Nexus AI engine is synchronous (ADR-0020): a scrape blocks until it finishes.
Serving that inside a request would tie up the event loop for the whole scrape, so
the runner submits each scrape to a bounded thread pool and returns immediately. The
engine itself already assigns a durable job id and persists job state through its
JobManager, so callers track progress by polling the jobs endpoints — the runner
only owns the *submission* and a small record of accepted submissions.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime

from nexusai_pro_api.logging_config import get_logger
from nexusai_pro_api.services.engine_gateway import EngineGateway

logger = get_logger("job_runner")


@dataclass(slots=True)
class Submission:
    """A record that the API accepted a scrape for background execution."""

    submission_id: str
    target: str
    dataset_id: str
    state: str = "accepted"  # accepted -> running -> finished | failed
    job_id: str | None = None
    error: str | None = None
    submitted_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class JobRunner:
    """Submits scrapes to a thread pool and tracks their acceptance records."""

    def __init__(self, gateway: EngineGateway, *, max_workers: int) -> None:
        self._gateway = gateway
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="scrape")
        self._submissions: dict[str, Submission] = {}
        self._lock = threading.Lock()

    def submit_scrape(
        self,
        submission_id: str,
        target: str,
        *,
        dataset_id: str,
        export_formats: tuple[str, ...],
        report_formats: tuple[str, ...],
    ) -> Submission:
        """Accept a scrape for background execution and return its record."""
        record = Submission(submission_id=submission_id, target=target, dataset_id=dataset_id)
        with self._lock:
            self._submissions[submission_id] = record

        def _run() -> None:
            record.state = "running"
            logger.info("scrape started submission=%s target=%s", submission_id, target)
            try:
                job = self._gateway.run_scrape(
                    target,
                    dataset_id=dataset_id,
                    export_formats=export_formats,
                    report_formats=report_formats,
                )
                record.job_id = job.job_id
                record.state = "finished"
                logger.info("scrape finished submission=%s job=%s", submission_id, job.job_id)
            except Exception as exc:
                record.state = "failed"
                record.error = str(exc)
                logger.exception("scrape failed submission=%s", submission_id)

        self._pool.submit(_run)
        return record

    def get_submission(self, submission_id: str) -> Submission | None:
        with self._lock:
            return self._submissions.get(submission_id)

    def shutdown(self) -> None:
        """Stop accepting work and wait for running scrapes to drain."""
        self._pool.shutdown(wait=True)
