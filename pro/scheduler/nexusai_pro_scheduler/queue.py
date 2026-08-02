"""A thread-safe job queue with delayed visibility for retries.

Jobs are ordered by their ``not_before`` time (immediately-ready jobs first). A
worker asks for the next *ready* job; if the earliest job is scheduled for the
future (a backoff retry), the queue reports how long to wait instead of returning it.
This keeps retries honouring their backoff without a busy loop.
"""

from __future__ import annotations

import heapq
import itertools
import threading
from datetime import datetime

from .models import QueuedJob


class JobQueue:
    """A min-heap of queued jobs keyed by readiness time, safe across threads."""

    def __init__(self) -> None:
        self._heap: list[tuple[float, int, QueuedJob]] = []
        self._counter = itertools.count()
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._closed = False

    def put(self, job: QueuedJob) -> None:
        ready = (job.not_before or datetime.now()).timestamp()
        with self._not_empty:
            heapq.heappush(self._heap, (ready, next(self._counter), job))
            self._not_empty.notify()

    def get_ready(self, *, timeout: float = 1.0) -> QueuedJob | None:
        """Return the next ready job, or None if none becomes ready within ``timeout``.

        Blocks up to ``timeout`` seconds. If the earliest job is not yet due, waits
        only until it becomes due (or the timeout), so backoff is respected.
        """
        with self._not_empty:
            deadline = datetime.now().timestamp() + timeout
            while not self._closed:
                if not self._heap:
                    remaining = deadline - datetime.now().timestamp()
                    if remaining <= 0 or not self._not_empty.wait(timeout=remaining):
                        return None
                    continue

                ready_at, _, job = self._heap[0]
                now = datetime.now().timestamp()
                if ready_at <= now:
                    heapq.heappop(self._heap)
                    return job

                # Earliest job is in the future: wait until it is due or we time out.
                wait_for = min(ready_at, deadline) - now
                if wait_for <= 0:
                    return None
                self._not_empty.wait(timeout=wait_for)
                if deadline - datetime.now().timestamp() <= 0:
                    return None
            return None

    def size(self) -> int:
        with self._lock:
            return len(self._heap)

    def close(self) -> None:
        with self._not_empty:
            self._closed = True
            self._not_empty.notify_all()
