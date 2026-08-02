"""Graceful shutdown coordination.

Shutdown is cooperative and bounded. The coordinator holds the cancellation
tokens of the active jobs; on a shutdown request it signals them all and waits up
to a grace period for them to stop cleanly -- checkpointing and releasing
resources as they go -- rather than killing them mid-write. If the grace period
expires, it reports which jobs were still running, so the caller can decide,
rather than corrupting state to exit faster.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from nexusai.application.runtime.cancellation import CancellationToken


@dataclass(frozen=True, slots=True, kw_only=True)
class ShutdownOutcome:
    """The result of a graceful shutdown attempt."""

    clean: bool
    still_active: tuple[str, ...]


class ShutdownCoordinator:
    """Signals active work to stop and waits, bounded by a grace period."""

    def __init__(self, *, grace_seconds: float = 30.0) -> None:
        self._grace = grace_seconds
        self._tokens: dict[str, CancellationToken] = {}
        self._active: dict[str, bool] = {}
        self._lock = threading.Lock()

    def register(self, job_id: str, token: CancellationToken) -> None:
        """Track a running job's cancellation token."""
        with self._lock:
            self._tokens[job_id] = token
            self._active[job_id] = True

    def complete(self, job_id: str) -> None:
        """Mark a job as no longer active."""
        with self._lock:
            self._active[job_id] = False

    def request_shutdown(self, *, poll_seconds: float = 0.05) -> ShutdownOutcome:
        """Signal every active job to cancel and wait up to the grace period."""
        with self._lock:
            for token in self._tokens.values():
                token.cancel()
        deadline = time.monotonic() + self._grace
        while time.monotonic() < deadline:
            if not self._any_active():
                return ShutdownOutcome(clean=True, still_active=())
            time.sleep(poll_seconds)
        return ShutdownOutcome(clean=False, still_active=self._active_ids())

    def _any_active(self) -> bool:
        with self._lock:
            return any(self._active.values())

    def _active_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(job_id for job_id, active in self._active.items() if active)
