"""Ports for logging, metrics, time and identity.

Time and identity are ports rather than direct calls to ``datetime.now()`` and
``uuid4()`` because both are effects. Injecting them is what allows a test to
freeze the clock and make identifiers deterministic, which in turn is what makes
assertions about logs, events and run records possible at all.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from nexusai.domain.observability.resources import ResourceSample


@runtime_checkable
class Logger(Protocol):
    """Structured logger.

    Implementations attach contextual fields (correlation id, job id, site id,
    module, stage) automatically. Callers supply only what is specific to the
    event being logged.
    """

    def debug(self, message: str, /, **fields: Any) -> None:
        """Log diagnostic detail useful only when investigating a problem."""
        ...

    def info(self, message: str, /, **fields: Any) -> None:
        """Log a normal, noteworthy occurrence."""
        ...

    def warning(self, message: str, /, **fields: Any) -> None:
        """Log a recoverable problem that an operator should eventually see."""
        ...

    def error(self, message: str, /, **fields: Any) -> None:
        """Log a failure that prevented an operation from completing."""
        ...

    def critical(self, message: str, /, **fields: Any) -> None:
        """Log a failure that prevents the framework from continuing."""
        ...

    def exception(self, message: str, /, **fields: Any) -> None:
        """Log a failure together with the active exception's traceback."""
        ...

    def bind(self, **fields: Any) -> Logger:
        """Return a logger that attaches ``fields`` to every subsequent record."""
        ...


@runtime_checkable
class MetricsSink(Protocol):
    """Destination for operational metrics."""

    def increment(
        self, name: str, value: int = 1, *, tags: Mapping[str, str] | None = None
    ) -> None:
        """Increase a counter by ``value``."""
        ...

    def gauge(self, name: str, value: float, *, tags: Mapping[str, str] | None = None) -> None:
        """Record the current value of a measurement."""
        ...

    def timing(self, name: str, seconds: float, *, tags: Mapping[str, str] | None = None) -> None:
        """Record how long an operation took, in seconds."""
        ...


@runtime_checkable
class Clock(Protocol):
    """Source of time."""

    def now(self) -> datetime:
        """Return the current time as a timezone-aware UTC datetime."""
        ...

    def monotonic(self) -> float:
        """Return a monotonically increasing counter, in seconds.

        Used for measuring durations, where wall-clock time is unsafe because it
        can move backwards.
        """
        ...


@runtime_checkable
class IdGenerator(Protocol):
    """Source of unique identifiers."""

    def new(self) -> str:
        """Return a new globally unique identifier."""
        ...


@runtime_checkable
class MetricSink(Protocol):
    """A vendor-neutral sink for recording and reading metrics.

    This is the richer metric contract the observability layer records into and
    reads back: counters and gauges with bounded dimensions, histogram/timer
    observations, and typed accessors for summaries. The application depends on
    this port; a concrete in-memory registry (or, later, a vendor exporter)
    implements it. Distinct from :class:`MetricsSink`, the lightweight fire-and-
    forget sink from the framework's foundation.
    """

    def increment(
        self, name: str, value: float = 1.0, *, dimensions: Mapping[str, str] | None = None
    ) -> None:
        """Add ``value`` to a counter."""
        ...

    def gauge(
        self, name: str, value: float, *, dimensions: Mapping[str, str] | None = None
    ) -> None:
        """Set a gauge to ``value``."""
        ...

    def observe(
        self, name: str, value: float, *, dimensions: Mapping[str, str] | None = None
    ) -> None:
        """Record a histogram or timer observation."""
        ...

    def counter_total(self, name: str) -> float:
        """Return a counter's total across all dimensions."""
        ...

    def counter_by_dimension(self, name: str, dimension: str) -> dict[str, float]:
        """Return a counter's totals grouped by one dimension's values."""
        ...

    def gauge_value(self, name: str) -> float | None:
        """Return a gauge's current value, or None if unset."""
        ...

    def snapshot(self) -> dict[str, object]:
        """Return a serialisable snapshot of every recorded metric."""
        ...


@runtime_checkable
class ResourceSamplerPort(Protocol):
    """A source of point-in-time process resource samples."""

    def sample(self) -> ResourceSample:
        """Take a resource sample."""
        ...

    @property
    def cpu_count(self) -> int | None:
        """The number of CPUs available, for interpreting utilisation."""
        ...
