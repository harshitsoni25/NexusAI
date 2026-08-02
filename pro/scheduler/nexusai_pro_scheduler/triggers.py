"""Compute the next run time for each schedule kind.

Daily/weekly/monthly are computed directly (clearer and free of cron edge cases),
while CRON defers to the cron engine and INTERVAL is a simple offset. All functions
return a timezone-naive local ``datetime`` at minute resolution.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .cron import parse_cron
from .models import Schedule, ScheduleKind


def _parse_hhmm(at: str | None) -> tuple[int, int]:
    if not at:
        raise ValueError("schedule requires 'at' in HH:MM form")
    hours, minutes = at.split(":", 1)
    h, m = int(hours), int(minutes)
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(f"invalid time '{at}'")
    return h, m


def _last_day_of_month(year: int, month: int) -> int:
    nxt = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    return (nxt - timedelta(days=1)).day


def next_run(schedule: Schedule, after: datetime) -> datetime:
    """Return the next firing time strictly after ``after`` for ``schedule``."""
    base = after.replace(second=0, microsecond=0)

    if schedule.kind is ScheduleKind.CRON:
        return parse_cron(schedule.cron or "").next_after(base)

    if schedule.kind is ScheduleKind.INTERVAL:
        seconds = schedule.interval_seconds or 0
        if seconds <= 0:
            raise ValueError("interval schedule requires a positive interval_seconds")
        return base + timedelta(seconds=seconds)

    if schedule.kind is ScheduleKind.DAILY:
        h, m = _parse_hhmm(schedule.at)
        candidate = base.replace(hour=h, minute=m)
        if candidate <= base:
            candidate += timedelta(days=1)
        return candidate

    if schedule.kind is ScheduleKind.WEEKLY:
        h, m = _parse_hhmm(schedule.at)
        weekdays = schedule.weekdays or (0,)  # default Monday
        for delta in range(0, 8):
            day = base + timedelta(days=delta)
            candidate = day.replace(hour=h, minute=m)
            if day.weekday() in weekdays and candidate > base:
                return candidate
        raise ValueError("could not compute weekly next run")

    if schedule.kind is ScheduleKind.MONTHLY:
        h, m = _parse_hhmm(schedule.at)
        days = schedule.days or (1,)
        # Search this month and the next few for the earliest matching day > base.
        year, month = base.year, base.month
        for _ in range(0, 14):
            last = _last_day_of_month(year, month)
            for target in sorted(days):
                dom = min(target, last)  # clamp e.g. 31 -> 30/28
                candidate = datetime(year, month, dom, h, m)
                if candidate > base:
                    return candidate
            month += 1
            if month > 12:
                month = 1
                year += 1
        raise ValueError("could not compute monthly next run")

    raise ValueError(f"unsupported schedule kind: {schedule.kind}")
