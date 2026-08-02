"""The scheduling loop.

A single daemon thread wakes on a fixed tick, asks each enabled schedule for its next
run, and enqueues a job when that time has arrived. After firing, a schedule's next
run is recomputed from *now*, so a schedule fires at most once per due window even if
the tick is coarse. Enqueuing is decoupled from execution — the executor's worker pool
drains the queue — which gives background execution and natural backpressure.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime

from .models import QueuedJob, Schedule
from .queue import JobQueue
from .store import ScheduleStore
from .triggers import next_run

logger = logging.getLogger("nexusai_pro_scheduler.loop")


class SchedulerLoop:
    def __init__(self, store: ScheduleStore, queue: JobQueue, *, tick_seconds: float = 1.0) -> None:
        self._store = store
        self._queue = queue
        self._tick = tick_seconds
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def prime(self, schedule: Schedule, *, now: datetime | None = None) -> None:
        """Compute the initial next_run for a freshly added schedule."""
        now = now or datetime.now()
        if schedule.next_run is None and schedule.enabled:
            schedule.next_run = next_run(schedule, now)

    def start(self) -> None:
        # Prime any schedules that were added before start.
        for schedule in self._store.list_all():
            self.prime(schedule)
        self._thread = threading.Thread(target=self._run, name="scheduler-loop", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5.0)

    def _run(self) -> None:
        while not self._stop.wait(self._tick):
            self.tick()

    def tick(self, *, now: datetime | None = None) -> int:
        """Enqueue all schedules due at ``now``; return how many fired."""
        now = now or datetime.now()
        fired = 0
        for schedule in self._store.list_all():
            if not schedule.enabled:
                continue
            if schedule.next_run is None:
                schedule.next_run = next_run(schedule, now)
                continue
            if schedule.next_run <= now:
                self._enqueue(schedule, now)
                schedule.last_run = now
                schedule.next_run = next_run(schedule, now)
                fired += 1
        return fired

    def _enqueue(self, schedule: Schedule, now: datetime) -> None:
        logger.info("enqueue schedule=%s (%s)", schedule.name, schedule.kind.value)
        self._queue.put(
            QueuedJob(
                schedule_id=schedule.id,
                schedule_name=schedule.name,
                spec=schedule.spec,
                retry=schedule.retry,
                scheduled_for=schedule.next_run or now,
            )
        )
