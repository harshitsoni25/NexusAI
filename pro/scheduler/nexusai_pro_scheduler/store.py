"""In-memory storage for schedules and run history.

Kept deliberately simple and thread-safe. A durable SQLite-backed store could
implement the same small surface without changing the rest of the scheduler; the
service depends only on these methods.
"""

from __future__ import annotations

import threading
from collections import deque

from .models import JobRun, Schedule


class ScheduleStore:
    def __init__(self, *, history_limit: int = 500) -> None:
        self._schedules: dict[str, Schedule] = {}
        self._runs: deque[JobRun] = deque(maxlen=history_limit)
        self._lock = threading.Lock()

    # --- schedules ---------------------------------------------------------

    def add(self, schedule: Schedule) -> Schedule:
        with self._lock:
            self._schedules[schedule.id] = schedule
        return schedule

    def remove(self, schedule_id: str) -> bool:
        with self._lock:
            return self._schedules.pop(schedule_id, None) is not None

    def get(self, schedule_id: str) -> Schedule | None:
        with self._lock:
            return self._schedules.get(schedule_id)

    def list_all(self) -> list[Schedule]:
        with self._lock:
            return list(self._schedules.values())

    def set_enabled(self, schedule_id: str, enabled: bool) -> bool:
        with self._lock:
            schedule = self._schedules.get(schedule_id)
            if schedule is None:
                return False
            schedule.enabled = enabled
            return True

    # --- run history -------------------------------------------------------

    def record_run(self, run: JobRun) -> None:
        with self._lock:
            self._runs.appendleft(run)

    def runs(self, *, limit: int = 100) -> list[JobRun]:
        with self._lock:
            return list(self._runs)[:limit]
