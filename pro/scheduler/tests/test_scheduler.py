"""End-to-end scheduler behaviour with a fake runner: due -> queued -> executed,
retry with backoff, and notifications. A separate real-engine smoke confirms the
executor reuses the frozen engine."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta

import pytest

from nexusai_pro_scheduler import (
    CollectingNotifier,
    RetryPolicy,
    RunResult,
    RunState,
    Schedule,
    ScheduleKind,
    SchedulerService,
    ScrapeSpec,
)

SPEC = ScrapeSpec(target="https://example.com/products")


class FakeRunner:
    """A runner that records calls and can be told to fail N times first."""

    def __init__(self, *, fail_times: int = 0) -> None:
        self.calls = 0
        self._fail_times = fail_times
        self._lock = threading.Lock()

    def run(self, spec: ScrapeSpec) -> RunResult:
        with self._lock:
            self.calls += 1
            n = self.calls
        if n <= self._fail_times:
            raise RuntimeError(f"boom {n}")
        return RunResult(job_id=f"job-{n}", state="completed")


def _wait_until(predicate, timeout=5.0, interval=0.02):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(interval)
    return False


def test_due_schedule_is_executed_in_background():
    runner = FakeRunner()
    notifier = CollectingNotifier()
    service = SchedulerService(runner, workers=2, tick_seconds=0.05, notifiers=[notifier])
    # A daily schedule already past today -> due on the next tick.
    past = (datetime.now() - timedelta(minutes=1)).strftime("%H:%M")
    with service:
        service.add_daily("nightly", past, SPEC)
        # force next_run into the past so it fires immediately
        service.list_schedules()[0].next_run = datetime.now() - timedelta(seconds=1)
        assert _wait_until(lambda: runner.calls >= 1)
        assert _wait_until(
            lambda: any(n.state == RunState.SUCCEEDED for n in notifier.notifications)
        )
    runs = service.runs()
    assert any(r.state == RunState.SUCCEEDED for r in runs)


def test_retry_then_success_with_notifications():
    runner = FakeRunner(fail_times=2)  # fail twice, succeed on 3rd
    notifier = CollectingNotifier()
    retry = RetryPolicy(max_attempts=3, backoff_seconds=0.05, backoff_factor=1.0)
    service = SchedulerService(runner, workers=1, tick_seconds=0.05, notifiers=[notifier])
    schedule = Schedule(name="retryme", kind=ScheduleKind.DAILY, spec=SPEC, at="00:00", retry=retry)
    with service:
        service.add(schedule)
        schedule.next_run = datetime.now() - timedelta(seconds=1)
        assert _wait_until(lambda: runner.calls >= 3, timeout=5)
        assert _wait_until(
            lambda: any(n.state == RunState.SUCCEEDED for n in notifier.notifications)
        )
    states = [n.state for n in notifier.notifications]
    assert states.count(RunState.RETRYING) == 2
    assert RunState.SUCCEEDED in states


def test_retry_exhaustion_marks_dead():
    runner = FakeRunner(fail_times=99)  # always fails
    notifier = CollectingNotifier()
    retry = RetryPolicy(max_attempts=2, backoff_seconds=0.05, backoff_factor=1.0)
    service = SchedulerService(runner, workers=1, tick_seconds=0.05, notifiers=[notifier])
    schedule = Schedule(name="doomed", kind=ScheduleKind.DAILY, spec=SPEC, at="00:00", retry=retry)
    with service:
        service.add(schedule)
        schedule.next_run = datetime.now() - timedelta(seconds=1)
        assert _wait_until(
            lambda: any(n.state == RunState.DEAD for n in notifier.notifications), timeout=5
        )
    assert runner.calls == 2  # max_attempts


def test_tick_recomputes_next_run():
    runner = FakeRunner()
    service = SchedulerService(runner, workers=1, tick_seconds=10)
    schedule = Schedule(name="cronny", kind=ScheduleKind.CRON, spec=SPEC, cron="*/5 * * * *")
    service.add(schedule)
    schedule.next_run = datetime.now() - timedelta(seconds=1)
    before = schedule.next_run
    fired = service.tick_once()
    assert fired == 1
    assert schedule.next_run is not None and schedule.next_run > before


@pytest.mark.engine
def test_reuses_real_engine_smoke():
    """The default runner drives the frozen engine end to end."""
    from nexusai_pro_scheduler import EngineScrapeRunner

    runner = EngineScrapeRunner()
    result = runner.run(ScrapeSpec(target="https://example.com", export_formats=("csv", "json")))
    assert result.job_id
    assert result.state
