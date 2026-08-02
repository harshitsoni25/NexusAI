"""Daily/weekly/monthly next-run computation."""

from __future__ import annotations

from datetime import datetime

from nexusai_pro_scheduler.models import Schedule, ScheduleKind, ScrapeSpec
from nexusai_pro_scheduler.triggers import next_run

SPEC = ScrapeSpec(target="https://example.com")


def _sched(kind, **kw):
    return Schedule(name="t", kind=kind, spec=SPEC, **kw)


def test_daily_rolls_to_tomorrow():
    s = _sched(ScheduleKind.DAILY, at="09:00")
    assert next_run(s, datetime(2026, 1, 1, 8, 0)) == datetime(2026, 1, 1, 9, 0)
    assert next_run(s, datetime(2026, 1, 1, 9, 0)) == datetime(2026, 1, 2, 9, 0)


def test_weekly_picks_next_weekday():
    # Mondays and Wednesdays at 08:30; from Thursday Jan 1 2026 -> next Monday Jan 5
    s = _sched(ScheduleKind.WEEKLY, at="08:30", weekdays=(0, 2))
    nxt = next_run(s, datetime(2026, 1, 1, 12, 0))
    assert nxt == datetime(2026, 1, 5, 8, 30)


def test_monthly_clamps_short_months():
    # Day 31 at 00:00; February clamps to the 28th (2026 not a leap year)
    s = _sched(ScheduleKind.MONTHLY, at="00:00", days=(31,))
    nxt = next_run(s, datetime(2026, 2, 1, 0, 0))
    assert nxt == datetime(2026, 2, 28, 0, 0)


def test_monthly_next_day_this_month():
    s = _sched(ScheduleKind.MONTHLY, at="06:00", days=(15,))
    assert next_run(s, datetime(2026, 3, 1, 0, 0)) == datetime(2026, 3, 15, 6, 0)
