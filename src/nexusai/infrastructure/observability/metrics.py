"""Metric sink adapters."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


class NullMetricsSink:
    """Discards every metric.

    The default when metric collection is switched off. A null implementation
    rather than an optional dependency keeps every call site free of
    ``if metrics is not None`` checks.
    """

    def increment(
        self, name: str, value: int = 1, *, tags: Mapping[str, str] | None = None
    ) -> None:
        """Discard a counter increment."""
        return

    def gauge(self, name: str, value: float, *, tags: Mapping[str, str] | None = None) -> None:
        """Discard a measurement."""
        return

    def timing(self, name: str, seconds: float, *, tags: Mapping[str, str] | None = None) -> None:
        """Discard a duration."""
        return


@dataclass(frozen=True, slots=True)
class MetricPoint:
    """A single recorded measurement."""

    name: str
    value: float
    tags: Mapping[str, str]


@dataclass(slots=True)
class InMemoryMetricsSink:
    """Accumulates metrics in memory.

    Used by the reporting layer to summarise a run, and by tests to assert that
    a component measured what it claimed to measure.
    """

    counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    gauges: list[MetricPoint] = field(default_factory=list)
    timings: list[MetricPoint] = field(default_factory=list)

    def increment(
        self, name: str, value: int = 1, *, tags: Mapping[str, str] | None = None
    ) -> None:
        """Increase a tagged counter by ``value``."""
        self.counters[_key(name, tags)] += value

    def gauge(self, name: str, value: float, *, tags: Mapping[str, str] | None = None) -> None:
        """Record the current value of a measurement."""
        self.gauges.append(MetricPoint(name, value, dict(tags or {})))

    def timing(self, name: str, seconds: float, *, tags: Mapping[str, str] | None = None) -> None:
        """Record how long an operation took, in seconds."""
        self.timings.append(MetricPoint(name, seconds, dict(tags or {})))

    def snapshot(self) -> dict[str, Any]:
        """Return a serialisable view of everything recorded so far."""
        return {
            "counters": dict(self.counters),
            "gauges": [(point.name, point.value, dict(point.tags)) for point in self.gauges],
            "timings": [(point.name, point.value, dict(point.tags)) for point in self.timings],
        }

    def timings_for(self, name: str) -> Sequence[float]:
        """Return every duration recorded under ``name``."""
        return [point.value for point in self.timings if point.name == name]


def _key(name: str, tags: Mapping[str, str] | None) -> str:
    """Build a counter key that keeps differently tagged counters distinct."""
    if not tags:
        return name
    rendered = ",".join(f"{key}={value}" for key, value in sorted(tags.items()))
    return f"{name}[{rendered}]"
