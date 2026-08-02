"""A small, dependency-free cron engine for schedule timing.

Supports the standard five fields — minute hour day-of-month month day-of-week —
with ``*``, single values, ranges ``a-b``, steps ``*/n`` and ``a-b/n``, and lists
``a,b,c``. Day-of-week accepts 0 or 7 for Sunday (Vixie convention). When both
day-of-month and day-of-week are restricted, a match on *either* fires the job, as
standard cron does.

Only what a scraping scheduler needs (minute resolution, next-run computation) is
implemented; seconds and non-standard extensions are intentionally omitted.
"""

from __future__ import annotations

from datetime import datetime, timedelta

_FIELD_BOUNDS = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]  # min,hour,dom,month,dow(py: Mon=0)


class CronError(ValueError):
    """Raised when a cron expression cannot be parsed."""


def _parse_field(field: str, index: int) -> set[int]:
    low, high = _FIELD_BOUNDS[index]
    allowed: set[int] = set()

    for part in field.split(","):
        step = 1
        body = part
        if "/" in part:
            body, step_str = part.split("/", 1)
            if not step_str.isdigit() or int(step_str) == 0:
                raise CronError(f"invalid step in '{part}'")
            step = int(step_str)

        if body == "*":
            start, end = low, high
        elif "-" in body:
            a, b = body.split("-", 1)
            start, end = _to_int(a, index), _to_int(b, index)
        else:
            start = end = _to_int(body, index)

        if start > end:
            raise CronError(f"range start after end in '{part}'")
        allowed.update(range(start, end + 1, step))

    return allowed


def _to_int(token: str, index: int) -> int:
    if not token.lstrip("-").isdigit():
        raise CronError(f"non-numeric field value '{token}'")
    value = int(token)
    low, high = _FIELD_BOUNDS[index]
    # Day-of-week: accept 7 as Sunday, then normalise to Python's Mon=0..Sun=6.
    if index == 4:
        if value == 7:
            value = 0  # cron Sunday
        if value < 0 or value > 6:
            raise CronError(f"day-of-week out of range: {token}")
        # cron: 0=Sun..6=Sat  ->  python: Mon=0..Sun=6
        return (value + 6) % 7
    if value < low or value > high:
        raise CronError(f"value {value} out of range for field {index}")
    return value


class CronExpression:
    """A parsed cron expression that can compute its next firing time."""

    __slots__ = ("minutes", "hours", "doms", "months", "dows", "_dom_restricted", "_dow_restricted", "raw")

    def __init__(self, expression: str) -> None:
        fields = expression.split()
        if len(fields) != 5:
            raise CronError("cron expression must have exactly five fields")
        self.raw = expression
        self.minutes = _parse_field(fields[0], 0)
        self.hours = _parse_field(fields[1], 1)
        self.doms = _parse_field(fields[2], 2)
        self.months = _parse_field(fields[3], 3)
        self.dows = _parse_field(fields[4], 4)
        self._dom_restricted = fields[2] != "*"
        self._dow_restricted = fields[4] != "*"

    def matches(self, moment: datetime) -> bool:
        if moment.minute not in self.minutes:
            return False
        if moment.hour not in self.hours:
            return False
        if moment.month not in self.months:
            return False
        dom_ok = moment.day in self.doms
        dow_ok = moment.weekday() in self.dows
        # Standard cron: when both are restricted, either match fires.
        if self._dom_restricted and self._dow_restricted:
            return dom_ok or dow_ok
        if self._dom_restricted:
            return dom_ok
        if self._dow_restricted:
            return dow_ok
        return True

    def next_after(self, after: datetime) -> datetime:
        """The first matching minute strictly after ``after``."""
        candidate = (after.replace(second=0, microsecond=0)) + timedelta(minutes=1)
        # Bound the search to four years to guard against impossible expressions.
        limit = candidate + timedelta(days=366 * 4)
        while candidate <= limit:
            if self.matches(candidate):
                return candidate
            candidate += timedelta(minutes=1)
        raise CronError(f"no next run within four years for '{self.raw}'")


def parse_cron(expression: str) -> CronExpression:
    return CronExpression(expression)
