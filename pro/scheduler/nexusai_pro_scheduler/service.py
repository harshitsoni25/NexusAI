"""The scheduler service — the public entry point.

Wires the store, queue, scheduling loop and executor into one object with a small,
stable API: add/list/remove/enable schedules, start/stop background execution, and
read run history. Convenience constructors build cron/daily/weekly/monthly schedules
so callers do not touch the timing internals.
"""

from __future__ import annotations

from datetime import datetime

from .cron import parse_cron
from .executor import Executor
from .models import (
    JobRun,
    RetryPolicy,
    Schedule,
    ScheduleKind,
    ScrapeSpec,
)
from .notifications import CompositeNotifier, LoggingNotifier, Notifier
from .queue import JobQueue
from .runner import ScrapeRunner
from .scheduler import SchedulerLoop
from .store import ScheduleStore
from .triggers import next_run


class SchedulerService:
    def __init__(
        self,
        runner: ScrapeRunner,
        *,
        workers: int = 2,
        tick_seconds: float = 1.0,
        notifiers: list[Notifier] | None = None,
        history_limit: int = 500,
    ) -> None:
        self._store = ScheduleStore(history_limit=history_limit)
        self._queue = JobQueue()
        self._notifier = CompositeNotifier(*(notifiers or [LoggingNotifier()]))
        self._loop = SchedulerLoop(self._store, self._queue, tick_seconds=tick_seconds)
        self._executor = Executor(
            self._queue,
            runner,
            self._notifier,
            workers=workers,
            on_run=self._store.record_run,
        )
        self._started = False

    # --- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        if self._started:
            return
        self._executor.start()
        self._loop.start()
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        self._loop.stop()
        self._executor.stop()
        self._started = False

    def __enter__(self) -> SchedulerService:
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()

    # --- schedule management ----------------------------------------------

    def add(self, schedule: Schedule) -> Schedule:
        self._loop.prime(schedule)
        return self._store.add(schedule)

    def remove(self, schedule_id: str) -> bool:
        return self._store.remove(schedule_id)

    def enable(self, schedule_id: str, enabled: bool = True) -> bool:
        ok = self._store.set_enabled(schedule_id, enabled)
        schedule = self._store.get(schedule_id)
        if ok and schedule and enabled and schedule.next_run is None:
            schedule.next_run = next_run(schedule, datetime.now())
        return ok

    def list_schedules(self) -> list[Schedule]:
        return self._store.list_all()

    def get(self, schedule_id: str) -> Schedule | None:
        return self._store.get(schedule_id)

    def runs(self, *, limit: int = 100) -> list[JobRun]:
        return self._store.runs(limit=limit)

    def add_notifier(self, notifier: Notifier) -> None:
        self._notifier.add(notifier)

    # --- convenience builders ---------------------------------------------

    def add_cron(
        self, name: str, expression: str, spec: ScrapeSpec, *, retry: RetryPolicy | None = None
    ) -> Schedule:
        parse_cron(expression)  # validate up front
        return self._build(name, ScheduleKind.CRON, spec, retry, cron=expression)

    def add_daily(self, name: str, at: str, spec: ScrapeSpec, *, retry: RetryPolicy | None = None) -> Schedule:
        return self._build(name, ScheduleKind.DAILY, spec, retry, at=at)

    def add_weekly(
        self, name: str, at: str, weekdays: tuple[int, ...], spec: ScrapeSpec, *, retry: RetryPolicy | None = None
    ) -> Schedule:
        return self._build(name, ScheduleKind.WEEKLY, spec, retry, at=at, weekdays=weekdays)

    def add_monthly(
        self, name: str, at: str, days: tuple[int, ...], spec: ScrapeSpec, *, retry: RetryPolicy | None = None
    ) -> Schedule:
        return self._build(name, ScheduleKind.MONTHLY, spec, retry, at=at, days=days)

    def _build(
        self,
        name: str,
        kind: ScheduleKind,
        spec: ScrapeSpec,
        retry: RetryPolicy | None,
        *,
        cron: str | None = None,
        at: str | None = None,
        weekdays: tuple[int, ...] = (),
        days: tuple[int, ...] = (),
    ) -> Schedule:
        schedule = Schedule(name=name, kind=kind, spec=spec, cron=cron, at=at, weekdays=weekdays, days=days)
        if retry is not None:
            schedule.retry = retry
        return self.add(schedule)

    def tick_once(self, *, now: datetime | None = None) -> int:
        """Run one scheduling pass synchronously (used by tests)."""
        return self._loop.tick(now=now)

    @property
    def queue_size(self) -> int:
        return self._queue.size()

