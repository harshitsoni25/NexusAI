"""Scheduler service settings."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class SchedulerConfig:
    workers: int = int(os.environ.get("NEXUSAI_SCHED_WORKERS", "2"))
    tick_seconds: float = float(os.environ.get("NEXUSAI_SCHED_TICK", "1.0"))
    history_limit: int = int(os.environ.get("NEXUSAI_SCHED_HISTORY", "500"))
    webhook_url: str | None = os.environ.get("NEXUSAI_SCHED_WEBHOOK")
