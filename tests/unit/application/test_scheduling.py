"""Tests for scheduling: next-run computation, due detection, and overlap policy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from nexusai.application.scheduling.scheduler import (
    ScheduleError,
    Scheduler,
    next_run_after,
)
from nexusai.application.usecases.scheduling import ScheduleUseCases
from nexusai.domain.model.schedule import (
    OverlapPolicy,
    Schedule,
    ScheduleExpression,
    ScheduleKind,
)
from nexusai.infrastructure.persistence import (
    SqlAlchemyScheduleStore,
    create_session_factory,
    create_sqlite_engine,
    initialise_schema,
)
from nexusai.testing import FrozenClock, SequentialIdGenerator

_NOW = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)


class TestNextRun:
    def test_interval(self) -> None:
        expr = ScheduleExpression(kind=ScheduleKind.INTERVAL, interval_seconds=3600)
        assert next_run_after(expr, _NOW) == _NOW + timedelta(hours=1)

    def test_once_in_future(self) -> None:
        at = _NOW + timedelta(days=1)
        expr = ScheduleExpression(kind=ScheduleKind.ONCE, at=at)
        assert next_run_after(expr, _NOW) == at

    def test_once_in_past_is_none(self) -> None:
        expr = ScheduleExpression(kind=ScheduleKind.ONCE, at=_NOW - timedelta(days=1))
        assert next_run_after(expr, _NOW) is None

    def test_cron_daily_9am(self) -> None:
        expr = ScheduleExpression(kind=ScheduleKind.CRON, cron="0 9 * * *")
        result = next_run_after(expr, _NOW)
        assert result == datetime(2025, 1, 2, 9, 0, tzinfo=UTC)

    def test_invalid_interval_raises(self) -> None:
        expr = ScheduleExpression(kind=ScheduleKind.INTERVAL, interval_seconds=0)
        with pytest.raises(ScheduleError):
            next_run_after(expr, _NOW)

    def test_malformed_cron_raises(self) -> None:
        expr = ScheduleExpression(kind=ScheduleKind.CRON, cron="0 9 *")
        with pytest.raises(ScheduleError):
            next_run_after(expr, _NOW)


class TestOverlapPolicy:
    def _schedule(self, policy: OverlapPolicy) -> Schedule:
        return Schedule(
            schedule_id="s1",
            name="n",
            target="https://x",
            expression=ScheduleExpression(kind=ScheduleKind.INTERVAL, interval_seconds=60),
            overlap_policy=policy,
            next_run=_NOW - timedelta(minutes=1),
        )

    def test_due_returns_enabled_past_due(self) -> None:
        scheduler = Scheduler()
        due = scheduler.due([self._schedule(OverlapPolicy.SKIP)], now=_NOW)
        assert len(due) == 1

    def test_skip_when_active(self) -> None:
        decision = Scheduler().decide(self._schedule(OverlapPolicy.SKIP), active=True)
        assert not decision.should_run

    def test_allow_when_active(self) -> None:
        decision = Scheduler().decide(self._schedule(OverlapPolicy.ALLOW), active=True)
        assert decision.should_run

    def test_queue_when_active_does_not_run_now(self) -> None:
        decision = Scheduler().decide(self._schedule(OverlapPolicy.QUEUE), active=True)
        assert not decision.should_run

    def test_runs_when_idle(self) -> None:
        decision = Scheduler().decide(self._schedule(OverlapPolicy.SKIP), active=False)
        assert decision.should_run

    def test_disabled_is_not_due(self) -> None:
        disabled = Schedule(
            schedule_id="s2",
            name="n",
            target="https://x",
            expression=ScheduleExpression(kind=ScheduleKind.INTERVAL, interval_seconds=60),
            enabled=False,
            next_run=_NOW - timedelta(minutes=1),
        )
        assert Scheduler().due([disabled], now=_NOW) == []


class TestScheduleUseCases:
    def _uses(self) -> ScheduleUseCases:
        engine = create_sqlite_engine()
        initialise_schema(engine)
        store = SqlAlchemyScheduleStore(create_session_factory(engine))
        return ScheduleUseCases(store, clock=FrozenClock(), ids=SequentialIdGenerator())

    def test_create_computes_next_run(self) -> None:
        uses = self._uses()
        schedule = uses.create(
            name="daily",
            target="https://x",
            expression=ScheduleExpression(kind=ScheduleKind.INTERVAL, interval_seconds=3600),
        )
        assert schedule.next_run is not None

    def test_list_returns_created(self) -> None:
        uses = self._uses()
        uses.create(
            name="daily",
            target="https://x",
            expression=ScheduleExpression(kind=ScheduleKind.INTERVAL, interval_seconds=3600),
        )
        assert len(uses.list()) == 1

    def test_disable_then_delete(self) -> None:
        uses = self._uses()
        schedule = uses.create(
            name="daily",
            target="https://x",
            expression=ScheduleExpression(kind=ScheduleKind.INTERVAL, interval_seconds=3600),
        )
        disabled = uses.set_enabled(schedule.schedule_id, enabled=False)
        assert not disabled.enabled
        uses.delete(schedule.schedule_id)
        assert uses.list() == []
