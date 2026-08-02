"""Reusable timing instrumentation that preserves typing and exceptions.

A :class:`Timer` times a block of work and records the duration into the metrics
sink, honouring the current observability context. It is a context manager, so it
times exactly the block it wraps, and it records the elapsed time whether the
block succeeds or raises -- the exception propagates unchanged, and the timing is
still captured. The ``timed`` decorator is the same idea for a whole function.

Instrumentation never changes behaviour: it observes. A timer that fails to record
must not turn a successful operation into a failure, which is why recording is
wrapped so an observability fault is swallowed as a warning rather than raised
(see :mod:`nexusai.application.observability.safety`).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from functools import wraps
from typing import TypeVar

from nexusai.application.observability.safety import safely
from nexusai.domain.ports.observability import Clock

R = TypeVar("R")
Record = Callable[[str, float, "Mapping[str, str] | None"], None]


@contextmanager
def timer(
    clock: Clock,
    record: Callable[[str, float, Mapping[str, str] | None], None],
    name: str,
    *,
    dimensions: Mapping[str, str] | None = None,
) -> Iterator[None]:
    """Time the wrapped block and record its duration in seconds.

    The duration is recorded even if the block raises; the exception is not
    suppressed. Recording is fault-isolated, so an observability error never
    surfaces as a failure of the timed work.
    """
    start = clock.monotonic()
    try:
        yield
    finally:
        elapsed = max(0.0, clock.monotonic() - start)
        with safely("timer.record"):
            record(name, elapsed, dimensions)


def timed(
    clock: Clock,
    record: Callable[[str, float, Mapping[str, str] | None], None],
    name: str,
    *,
    dimensions: Mapping[str, str] | None = None,
) -> Callable[[Callable[..., R]], Callable[..., R]]:
    """Decorate a function so each call records its duration under ``name``."""

    def decorator(function: Callable[..., R]) -> Callable[..., R]:
        @wraps(function)
        def wrapper(*args: object, **kwargs: object) -> R:
            with timer(clock, record, name, dimensions=dimensions):
                return function(*args, **kwargs)

        return wrapper

    return decorator
