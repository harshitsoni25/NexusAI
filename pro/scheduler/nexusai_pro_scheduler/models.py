"""Domain models for the Nexus AI Pro scheduler.

These are plain dataclasses with no dependency on the engine. A ``Schedule`` describes
*when* and *what* to scrape; a ``QueuedJob`` is one due execution moving through the
queue; a ``JobRun`` records an attempt's outcome. The engine is reached only by the
executor, which turns a due ``Schedule`` into a scrape.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ScheduleKind(str, Enum):
    CRON = "cron"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    INTERVAL = "interval"


class RunState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD = "dead"  # exhausted retries


@dataclass(slots=True)
class RetryPolicy:
    """How a failed job is retried: capped attempts with exponential backoff."""

    max_attempts: int = 3
    backoff_seconds: float = 5.0
    backoff_factor: float = 2.0
    max_backoff_seconds: float = 300.0

    def delay_for(self, attempt: int) -> float:
        """Backoff before ``attempt`` (1-based). attempt=1 has no prior delay."""
        if attempt <= 1:
            return 0.0
        raw = self.backoff_seconds * (self.backoff_factor ** (attempt - 2))
        return min(raw, self.max_backoff_seconds)


@dataclass(slots=True)
class ScrapeSpec:
    """What to scrape when a schedule fires."""

    target: str
    dataset_id: str | None = None
    export_formats: tuple[str, ...] = ("csv", "json")
    report_formats: tuple[str, ...] = ("html", "json")


@dataclass(slots=True)
class Schedule:
    """A recurring instruction to run a scrape.

    Exactly one timing description is used, per ``kind``:
      * CRON     -> ``cron`` expression (5 fields).
      * DAILY    -> ``at`` (HH:MM).
      * WEEKLY   -> ``at`` + ``weekdays`` (0=Mon .. 6=Sun).
      * MONTHLY  -> ``at`` + ``days`` (1..31, clamped to month length).
      * INTERVAL -> ``interval_seconds``.
    """

    name: str
    kind: ScheduleKind
    spec: ScrapeSpec
    cron: str | None = None
    at: str | None = None  # "HH:MM"
    weekdays: tuple[int, ...] = ()
    days: tuple[int, ...] = ()
    interval_seconds: float | None = None
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    enabled: bool = True
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: datetime = field(default_factory=datetime.now)
    next_run: datetime | None = None
    last_run: datetime | None = None


@dataclass(slots=True)
class QueuedJob:
    """One due execution of a schedule as it moves through the queue."""

    schedule_id: str
    schedule_name: str
    spec: ScrapeSpec
    retry: RetryPolicy
    scheduled_for: datetime
    attempt: int = 1
    state: RunState = RunState.QUEUED
    job_id: str | None = None  # engine job id, once known
    error: str | None = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    not_before: datetime | None = None  # for delayed retries


@dataclass(slots=True)
class JobRun:
    """A recorded attempt outcome, kept for history."""

    schedule_id: str
    schedule_name: str
    attempt: int
    state: RunState
    started_at: datetime
    finished_at: datetime | None = None
    job_id: str | None = None
    error: str | None = None
