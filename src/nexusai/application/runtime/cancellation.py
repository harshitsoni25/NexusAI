"""Cooperative cancellation and bounded concurrency primitives.

Cancellation here is cooperative, not pre-emptive: a :class:`CancellationToken`
carries an intent that running work polls at safe points and honours by stopping
cleanly, saving a checkpoint and releasing resources. Nothing is killed
mid-write. The token is thread-safe so a signal handler or a supervising thread
can request cancellation while work runs.

:class:`ConcurrencyLimiter` bounds how much runs at once, and :class:`BoundedQueue`
bounds how much waits to run, together giving the application backpressure: when
consumers fall behind, producers block on a full queue rather than accumulating
unbounded work.
"""

from __future__ import annotations

import queue
import threading
from types import TracebackType

from nexusai.domain.errors.exceptions import NexusAIError


class CancelledError(NexusAIError):
    """Raised at a cancellation checkpoint when cancellation has been requested."""


class CancellationToken:
    """A thread-safe, cooperative cancellation signal.

    Work checks :meth:`is_cancelled` (or calls :meth:`raise_if_cancelled`) at safe
    points; a supervisor calls :meth:`cancel`. Cancellation is one-way: once set,
    it stays set.
    """

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        """Request cancellation. Idempotent."""
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        """Whether cancellation has been requested."""
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        """Raise :class:`CancelledError` if cancellation has been requested."""
        if self._event.is_set():
            raise CancelledError("Operation was cancelled")

    def wait(self, timeout: float) -> bool:
        """Block up to ``timeout`` seconds; return whether cancellation occurred."""
        return self._event.wait(timeout)


class ConcurrencyLimiter:
    """A bounded gate limiting how many units of work run concurrently.

    Used as a context manager around a unit of work; acquiring blocks while the
    limit is reached, which is one half of the application's backpressure.
    """

    def __init__(self, limit: int) -> None:
        if limit < 1:
            raise ValueError("concurrency limit must be at least 1")
        self._limit = limit
        self._semaphore = threading.BoundedSemaphore(limit)

    @property
    def limit(self) -> int:
        """The maximum number of concurrent holders."""
        return self._limit

    def acquire(self, *, timeout: float | None = None) -> bool:
        """Acquire a slot, blocking up to ``timeout`` seconds."""
        if timeout is None:
            return self._semaphore.acquire()
        return self._semaphore.acquire(timeout=timeout)

    def release(self) -> None:
        """Release a previously acquired slot."""
        self._semaphore.release()

    def __enter__(self) -> ConcurrencyLimiter:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()


class BoundedQueue[T]:
    """A fixed-capacity queue that blocks producers when full.

    The other half of backpressure: a producer submitting faster than consumers
    drain blocks on :meth:`put` once capacity is reached, rather than growing the
    queue without limit.
    """

    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("queue capacity must be at least 1")
        self._capacity = capacity
        self._queue: queue.Queue[T] = queue.Queue(maxsize=capacity)

    @property
    def capacity(self) -> int:
        """The maximum number of queued items."""
        return self._capacity

    def put(self, item: T, *, timeout: float | None = None) -> bool:
        """Enqueue ``item``, blocking if full. Return ``False`` on timeout."""
        try:
            self._queue.put(item, timeout=timeout)
        except queue.Full:
            return False
        return True

    def get(self, *, timeout: float | None = None) -> T | None:
        """Dequeue an item, blocking if empty. Return ``None`` on timeout."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def __len__(self) -> int:
        return self._queue.qsize()

    @property
    def empty(self) -> bool:
        """Whether the queue currently holds no items."""
        return self._queue.empty()
