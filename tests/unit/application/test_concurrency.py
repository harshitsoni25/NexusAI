"""Tests for concurrency bounds, backpressure, cancellation, and shutdown."""

from __future__ import annotations

import pytest

from nexusai.application.runtime.cancellation import (
    BoundedQueue,
    CancellationToken,
    CancelledError,
    ConcurrencyLimiter,
)
from nexusai.application.runtime.shutdown import ShutdownCoordinator


class TestCancellation:
    def test_starts_uncancelled(self) -> None:
        assert not CancellationToken().is_cancelled

    def test_cancel_is_observable(self) -> None:
        token = CancellationToken()
        token.cancel()
        assert token.is_cancelled

    def test_raise_if_cancelled(self) -> None:
        token = CancellationToken()
        token.cancel()
        with pytest.raises(CancelledError):
            token.raise_if_cancelled()

    def test_raise_if_not_cancelled_is_noop(self) -> None:
        CancellationToken().raise_if_cancelled()


class TestConcurrencyLimiter:
    def test_bounds_concurrent_holders(self) -> None:
        limiter = ConcurrencyLimiter(2)
        assert limiter.acquire(timeout=0.1)
        assert limiter.acquire(timeout=0.1)
        assert not limiter.acquire(timeout=0.05)
        limiter.release()
        assert limiter.acquire(timeout=0.1)

    def test_rejects_zero_limit(self) -> None:
        with pytest.raises(ValueError, match="at least 1"):
            ConcurrencyLimiter(0)

    def test_context_manager_releases(self) -> None:
        limiter = ConcurrencyLimiter(1)
        with limiter:
            assert not limiter.acquire(timeout=0.05)
        assert limiter.acquire(timeout=0.1)


class TestBoundedQueue:
    def test_backpressure_when_full(self) -> None:
        queue: BoundedQueue[int] = BoundedQueue(1)
        assert queue.put(1, timeout=0.1)
        assert not queue.put(2, timeout=0.05)

    def test_get_returns_items_then_times_out(self) -> None:
        queue: BoundedQueue[int] = BoundedQueue(2)
        queue.put(1)
        assert queue.get(timeout=0.1) == 1
        assert queue.get(timeout=0.05) is None

    def test_rejects_zero_capacity(self) -> None:
        with pytest.raises(ValueError, match="at least 1"):
            BoundedQueue(0)

    def test_len_and_empty(self) -> None:
        queue: BoundedQueue[int] = BoundedQueue(2)
        assert queue.empty
        queue.put(1)
        assert len(queue) == 1


class TestShutdown:
    def test_clean_shutdown_when_no_active_jobs(self) -> None:
        coordinator = ShutdownCoordinator(grace_seconds=1.0)
        token = CancellationToken()
        coordinator.register("j1", token)
        coordinator.complete("j1")
        outcome = coordinator.request_shutdown()
        assert outcome.clean
        assert token.is_cancelled

    def test_reports_still_active_after_grace(self) -> None:
        coordinator = ShutdownCoordinator(grace_seconds=0.1)
        coordinator.register("j1", CancellationToken())
        outcome = coordinator.request_shutdown(poll_seconds=0.02)
        assert not outcome.clean
        assert "j1" in outcome.still_active
