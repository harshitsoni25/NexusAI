"""The schedule model for recurring jobs.

A schedule is a stored intention to run a job, on a one-time, interval or
cron-like cadence. It is pure data: computing the next run and deciding whether to
run belong to the scheduling service, and executing belongs to the orchestrator.
Keeping the schedule inert means it can be persisted, listed and edited without
any runner being involved.

The overlap policy is part of the model because it is a safety property: a
schedule that fires while its previous run is still active must have a defined
answer -- allow, skip, or queue -- rather than silently starting unbounded
concurrent runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class ScheduleKind(Enum):
    """How a schedule recurs."""

    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"


class OverlapPolicy(Enum):
    """What happens when a schedule fires while its last run is still active."""

    ALLOW = "allow"
    SKIP = "skip"
    QUEUE = "queue"


@dataclass(frozen=True, slots=True, kw_only=True)
class ScheduleExpression:
    """When a schedule fires.

    Exactly one cadence is meaningful per kind: ``ONCE`` uses ``at``, ``INTERVAL``
    uses ``interval_seconds``, and ``CRON`` uses a five-field ``cron`` string.

    Attributes:
        kind: The recurrence kind.
        at: The single fire time, for a one-time schedule.
        interval_seconds: The gap between runs, for an interval schedule.
        cron: A five-field cron expression, for a cron schedule.
    """

    kind: ScheduleKind
    at: datetime | None = None
    interval_seconds: float | None = None
    cron: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "kind": self.kind.value,
            "at": self.at.isoformat() if self.at else None,
            "interval_seconds": self.interval_seconds,
            "cron": self.cron,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class Schedule:
    """A stored, recurring intention to run a job.

    Attributes:
        schedule_id: The schedule's identity.
        name: A human-readable name.
        target: The site or URL to scrape.
        expression: When the schedule fires.
        enabled: Whether the schedule is active.
        overlap_policy: What to do when a run is still active at fire time.
        configuration_ref: The configuration to run under.
        created_at: When the schedule was created.
        last_run: When the schedule last fired.
        next_run: When the schedule will next fire.
        last_result: The state of the last run.
    """

    schedule_id: str
    name: str
    target: str
    expression: ScheduleExpression
    enabled: bool = True
    overlap_policy: OverlapPolicy = OverlapPolicy.SKIP
    configuration_ref: str | None = None
    created_at: datetime | None = None
    last_run: datetime | None = None
    next_run: datetime | None = None
    last_result: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "schedule_id": self.schedule_id,
            "name": self.name,
            "target": self.target,
            "expression": self.expression.to_dict(),
            "enabled": self.enabled,
            "overlap_policy": self.overlap_policy.value,
            "configuration_ref": self.configuration_ref,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "last_result": self.last_result,
        }


def next_interval_run(last: datetime, interval_seconds: float) -> datetime:
    """Return the next fire time for an interval schedule after ``last``."""
    return last + timedelta(seconds=interval_seconds)
