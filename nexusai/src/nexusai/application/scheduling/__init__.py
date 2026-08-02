"""Local scheduling foundation.

Holds the scheduler, which decides which schedules are due and whether an overlap
policy permits a due schedule to run. It computes and decides only; running the
resulting job belongs to a use case, keeping scheduling separate from execution.
"""

from __future__ import annotations

from nexusai.application.scheduling.scheduler import (
    ScheduleError,
    Scheduler,
    TriggerDecision,
    next_run_after,
)

__all__ = ["ScheduleError", "Scheduler", "TriggerDecision", "next_run_after"]
