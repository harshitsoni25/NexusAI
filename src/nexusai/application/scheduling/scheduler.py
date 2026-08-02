"""Local scheduling: deciding when schedules are due and honouring overlap policy.

The scheduler computes when a schedule should next fire and, given the current
time, which schedules are due -- and nothing more. It does not run jobs, own a
thread, or keep a daemon alive; triggering a due schedule is the caller's job,
through a use case, which keeps scheduling firmly separate from execution.

Overlap is the safety concern it does enforce. When a schedule falls due while its
previous run is still active, the policy decides the outcome -- allow a concurrent
run, skip this occurrence, or queue it -- so a slow job can never cause unbounded
concurrent runs to pile up behind a fast cadence.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from nexusai.domain.errors.exceptions import NexusAIError
from nexusai.domain.model.schedule import (
    OverlapPolicy,
    Schedule,
    ScheduleExpression,
    ScheduleKind,
)


class ScheduleError(NexusAIError):
    """A schedule expression is invalid or cannot be evaluated."""


@dataclass(frozen=True, slots=True, kw_only=True)
class TriggerDecision:
    """Whether a due schedule should fire now, and why."""

    schedule_id: str
    should_run: bool
    reason: str


def next_run_after(expression: ScheduleExpression, after: datetime) -> datetime | None:
    """Return the next fire time strictly after ``after``, or ``None`` if none.

    Raises:
        ScheduleError: If the expression is missing the field its kind requires.
    """
    if expression.kind is ScheduleKind.ONCE:
        if expression.at is None:
            raise ScheduleError("A one-time schedule needs a fire time")
        return expression.at if expression.at > after else None

    if expression.kind is ScheduleKind.INTERVAL:
        if not expression.interval_seconds or expression.interval_seconds <= 0:
            raise ScheduleError("An interval schedule needs a positive interval")
        return after + timedelta(seconds=expression.interval_seconds)

    return _next_cron(expression, after)


def _next_cron(expression: ScheduleExpression, after: datetime) -> datetime:
    """Compute the next matching minute for a five-field cron expression.

    Supports ``*`` and comma-separated integer lists in each of the five fields
    (minute, hour, day-of-month, month, day-of-week). This is a deliberately
    small cron: enough for common recurring cadences without a new dependency.
    """
    if not expression.cron:
        raise ScheduleError("A cron schedule needs a cron expression")
    fields = expression.cron.split()
    if len(fields) != 5:
        raise ScheduleError("A cron expression must have five fields")
    minute, hour, dom, month, dow = (_parse_field(f) for f in fields)

    candidate = (after + timedelta(minutes=1)).replace(second=0, microsecond=0)
    for _ in range(_CRON_SEARCH_LIMIT):
        if (
            (minute is None or candidate.minute in minute)
            and (hour is None or candidate.hour in hour)
            and (dom is None or candidate.day in dom)
            and (month is None or candidate.month in month)
            and (dow is None or candidate.weekday() in _to_python_dow(dow))
        ):
            return candidate
        candidate += timedelta(minutes=1)
    raise ScheduleError("No cron match found within the search window")


_CRON_SEARCH_LIMIT = 366 * 24 * 60


def _parse_field(field: str) -> set[int] | None:
    if field == "*":
        return None
    values: set[int] = set()
    for part in field.split(","):
        values.add(int(part))
    return values


def _to_python_dow(values: set[int]) -> set[int]:
    # Cron day-of-week: 0 = Sunday. Python weekday(): 0 = Monday.
    return {(day - 1) % 7 for day in values}


class Scheduler:
    """Decides which schedules are due and whether they may run."""

    def due(self, schedules: Sequence[Schedule], *, now: datetime) -> list[Schedule]:
        """Return the enabled schedules whose next run is at or before ``now``."""
        result: list[Schedule] = []
        for schedule in schedules:
            if not schedule.enabled:
                continue
            if schedule.next_run is not None and schedule.next_run <= now:
                result.append(schedule)
        return result

    def decide(self, schedule: Schedule, *, active: bool) -> TriggerDecision:
        """Apply the overlap policy to a due schedule with an ``active`` run."""
        if not active:
            return TriggerDecision(
                schedule_id=schedule.schedule_id, should_run=True, reason="no active run"
            )
        if schedule.overlap_policy is OverlapPolicy.ALLOW:
            return TriggerDecision(
                schedule_id=schedule.schedule_id, should_run=True, reason="overlap allowed"
            )
        if schedule.overlap_policy is OverlapPolicy.SKIP:
            return TriggerDecision(
                schedule_id=schedule.schedule_id,
                should_run=False,
                reason="skipped: previous run still active",
            )
        return TriggerDecision(
            schedule_id=schedule.schedule_id,
            should_run=False,
            reason="queued: previous run still active",
        )
