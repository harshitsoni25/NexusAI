"""Cron parsing and next-run computation."""

from __future__ import annotations

from datetime import datetime

import pytest

from nexusai_pro_scheduler.cron import CronError, parse_cron


def test_every_minute():
    expr = parse_cron("* * * * *")
    now = datetime(2026, 1, 1, 10, 0)
    assert expr.next_after(now) == datetime(2026, 1, 1, 10, 1)


def test_specific_time_daily():
    expr = parse_cron("30 9 * * *")
    assert expr.next_after(datetime(2026, 1, 1, 8, 0)) == datetime(2026, 1, 1, 9, 30)
    assert expr.next_after(datetime(2026, 1, 1, 10, 0)) == datetime(2026, 1, 2, 9, 30)


def test_step_and_range():
    expr = parse_cron("*/15 * * * *")
    assert expr.next_after(datetime(2026, 1, 1, 10, 2)) == datetime(2026, 1, 1, 10, 15)
    rng = parse_cron("0 9-17 * * *")
    assert rng.next_after(datetime(2026, 1, 1, 17, 30)) == datetime(2026, 1, 2, 9, 0)


def test_day_of_week_sunday_both_conventions():
    # cron dow 0 and 7 are both Sunday
    for expr_str in ("0 12 * * 0", "0 12 * * 7"):
        expr = parse_cron(expr_str)
        nxt = expr.next_after(datetime(2026, 1, 1, 0, 0))  # 2026-01-01 is a Thursday
        assert nxt.weekday() == 6  # Sunday
        assert (nxt.hour, nxt.minute) == (12, 0)


def test_dom_or_dow_semantics():
    # Both restricted -> either matches (fires on the 1st OR any Monday)
    expr = parse_cron("0 0 1 * 1")
    nxt = expr.next_after(datetime(2026, 1, 2, 0, 0))  # Fri Jan 2
    assert nxt == datetime(2026, 1, 5, 0, 0)  # next Monday


def test_invalid_expressions():
    with pytest.raises(CronError):
        parse_cron("* * * *")  # too few fields
    with pytest.raises(CronError):
        parse_cron("99 * * * *")  # out of range
