"""Background execution of queued jobs with retry and notifications.

A pool of worker threads pulls ready jobs from the queue and runs each scrape through
the ``ScrapeRunner``. On failure the job is re-queued with backoff until its retry
policy is exhausted, after which it is marked dead. Every transition emits a
notification. Execution is synchronous per job (the engine is synchronous, ADR-0020);
concurrency comes from the pool, not from asyncio.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime, timedelta

from .models import JobRun, QueuedJob, RunState
from .notifications import CompositeNotifier, Notification
from .queue import JobQueue
from .runner import ScrapeRunner

logger = logging.getLogger("nexusai_pro_scheduler.executor")


class Executor:
    """Runs queued jobs on a fixed pool of worker threads."""

    def __init__(
        self,
        queue: JobQueue,
        runner: ScrapeRunner,
        notifier: CompositeNotifier,
        *,
        workers: int = 2,
        on_run: Callable[[JobRun], None] | None = None,
    ) -> None:
        self._queue = queue
        self._runner = runner
        self._notifier = notifier
        self._workers = workers
        self._threads: list[threading.Thread] = []
        self._stop = threading.Event()
        self._on_run = on_run

    def start(self) -> None:
        for i in range(self._workers):
            thread = threading.Thread(target=self._loop, name=f"scheduler-worker-{i}", daemon=True)
            thread.start()
            self._threads.append(thread)

    def stop(self) -> None:
        self._stop.set()
        self._queue.close()
        for thread in self._threads:
            thread.join(timeout=5.0)

    def _loop(self) -> None:
        while not self._stop.is_set():
            job = self._queue.get_ready(timeout=0.5)
            if job is None:
                continue
            self._execute(job)

    def _execute(self, job: QueuedJob) -> None:
        job.state = RunState.RUNNING
        started = datetime.now()
        logger.info("running schedule=%s attempt=%d", job.schedule_name, job.attempt)
        try:
            result = self._runner.run(job.spec)
            job.job_id = result.job_id
            job.state = RunState.SUCCEEDED
            self._record(job, started, RunState.SUCCEEDED)
            self._notify(job, RunState.SUCCEEDED, f"completed as job {result.job_id}")
        except Exception as exc:  # noqa: BLE001 - failure drives the retry policy
            job.error = str(exc)
            logger.warning("schedule=%s attempt=%d failed: %s", job.schedule_name, job.attempt, exc)
            if job.attempt < job.retry.max_attempts:
                self._requeue(job)
            else:
                job.state = RunState.DEAD
                self._record(job, started, RunState.DEAD)
                self._notify(job, RunState.DEAD, f"failed after {job.attempt} attempts: {exc}")

    def _requeue(self, job: QueuedJob) -> None:
        next_attempt = job.attempt + 1
        delay = job.retry.delay_for(next_attempt)
        retry_job = QueuedJob(
            schedule_id=job.schedule_id,
            schedule_name=job.schedule_name,
            spec=job.spec,
            retry=job.retry,
            scheduled_for=job.scheduled_for,
            attempt=next_attempt,
            state=RunState.RETRYING,
            not_before=datetime.now() + timedelta(seconds=delay),
        )
        self._notify(job, RunState.RETRYING, f"retry {next_attempt}/{job.retry.max_attempts} in {delay:.0f}s")
        self._queue.put(retry_job)

    def _record(self, job: QueuedJob, started: datetime, state: RunState) -> None:
        if self._on_run:
            self._on_run(
                JobRun(
                    schedule_id=job.schedule_id,
                    schedule_name=job.schedule_name,
                    attempt=job.attempt,
                    state=state,
                    started_at=started,
                    finished_at=datetime.now(),
                    job_id=job.job_id,
                    error=job.error,
                )
            )

    def _notify(self, job: QueuedJob, state: RunState, message: str) -> None:
        self._notifier.emit(
            Notification(
                schedule_id=job.schedule_id,
                schedule_name=job.schedule_name,
                state=state,
                attempt=job.attempt,
                message=message,
                job_id=job.job_id,
            )
        )
