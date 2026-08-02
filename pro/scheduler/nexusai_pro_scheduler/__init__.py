"""Nexus AI Pro scheduler — cron/daily/weekly/monthly scheduling with a job queue,
background execution, retry with backoff, and notifications. Reuses the certified
Nexus AI engine as a library; the engine is never modified."""

from .config import SchedulerConfig
from .cron import CronError, parse_cron
from .models import (
    JobRun,
    QueuedJob,
    RetryPolicy,
    RunState,
    Schedule,
    ScheduleKind,
    ScrapeSpec,
)
from .notifications import (
    CollectingNotifier,
    CompositeNotifier,
    ConsoleNotifier,
    LoggingNotifier,
    Notification,
    Notifier,
    WebhookNotifier,
)
from .runner import EngineScrapeRunner, RunResult, ScrapeRunner
from .service import SchedulerService
from .triggers import next_run

__all__ = [
    "SchedulerConfig",
    "SchedulerService",
    "Schedule",
    "ScheduleKind",
    "ScrapeSpec",
    "RetryPolicy",
    "RunState",
    "QueuedJob",
    "JobRun",
    "EngineScrapeRunner",
    "ScrapeRunner",
    "RunResult",
    "next_run",
    "parse_cron",
    "CronError",
    "Notifier",
    "Notification",
    "LoggingNotifier",
    "ConsoleNotifier",
    "WebhookNotifier",
    "CollectingNotifier",
    "CompositeNotifier",
]
