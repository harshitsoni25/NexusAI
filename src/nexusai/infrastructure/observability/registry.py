"""A vendor-neutral, in-memory metrics registry.

This is the concrete collector the framework records into. It implements the four
metric kinds -- counter, gauge, histogram, timer -- keyed by name and a small set
of bounded dimensions, and it is safe to record into from several threads at
once, because concurrent jobs share one registry. It depends on no monitoring
vendor: an OpenTelemetry or Prometheus exporter would read the registry's
snapshot, not replace it.

Cardinality is governed against the catalog. A metric may only be recorded with
the dimensions its :class:`~nexusai.domain.observability.metrics.MetricDefinition`
allows, and dimension values are expected to be bounded categories; this is what
keeps an aggregated metric from exploding into a label per URL.
"""

from __future__ import annotations

import math
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from nexusai.domain.observability.metrics import (
    MetricDefinition,
    MetricType,
    is_valid_metric_name,
)


class MetricError(Exception):
    """A metric was recorded in a way the catalog does not permit."""


@dataclass(frozen=True, slots=True)
class _Key:
    name: str
    dimensions: tuple[tuple[str, str], ...]


@dataclass(slots=True)
class HistogramValue:
    """The accumulated observations of a histogram or timer."""

    samples: list[float] = field(default_factory=list)

    def observe(self, value: float) -> None:
        """Record one observation."""
        self.samples.append(value)

    def percentile(self, fraction: float) -> float | None:
        """Return the value at ``fraction`` (0..1) using nearest-rank, or None."""
        if not self.samples:
            return None
        ordered = sorted(self.samples)
        rank = max(0, math.ceil(fraction * len(ordered)) - 1)
        return ordered[min(rank, len(ordered) - 1)]

    def summary(self, *, min_samples: int = 20) -> dict[str, object]:
        """Summarise the distribution.

        Percentiles are reported only when at least ``min_samples`` observations
        exist; below that, they would misrepresent noise as signal, so they are
        returned as ``None`` with the sample count made explicit.
        """
        count = len(self.samples)
        base: dict[str, object] = {
            "count": count,
            "sum": sum(self.samples),
            "min": min(self.samples) if self.samples else None,
            "max": max(self.samples) if self.samples else None,
            "mean": (sum(self.samples) / count) if count else None,
        }
        sufficient = count >= min_samples
        base["percentiles_reliable"] = sufficient
        base["p50"] = self.percentile(0.50) if sufficient else None
        base["p90"] = self.percentile(0.90) if sufficient else None
        base["p95"] = self.percentile(0.95) if sufficient else None
        base["p99"] = self.percentile(0.99) if sufficient else None
        return base


class MetricsRegistry:
    """A concurrency-safe, in-memory registry of counters, gauges and histograms."""

    def __init__(
        self, catalog: Mapping[str, MetricDefinition] | None = None, *, min_samples: int = 20
    ) -> None:
        self._catalog = dict(catalog or {})
        self._min_samples = min_samples
        self._counters: dict[_Key, float] = {}
        self._gauges: dict[_Key, float] = {}
        self._histograms: dict[_Key, HistogramValue] = {}
        self._lock = threading.Lock()

    def _key(self, name: str, dimensions: Mapping[str, str] | None) -> _Key:
        if not is_valid_metric_name(name):
            raise MetricError(f"invalid metric name: {name!r}")
        dims = dict(dimensions or {})
        definition = self._catalog.get(name)
        if definition is not None:
            allowed = set(definition.dimensions)
            unknown = set(dims) - allowed
            if unknown:
                raise MetricError(f"metric {name!r} does not allow dimensions {sorted(unknown)}")
        for value in dims.values():
            if len(value) > 64:
                raise MetricError(f"dimension value too long for {name!r}; use a bounded category")
        return _Key(name=name, dimensions=tuple(sorted(dims.items())))

    def _check_type(self, name: str, expected: MetricType) -> None:
        definition = self._catalog.get(name)
        if definition is not None and definition.metric_type is not expected:
            raise MetricError(
                f"metric {name!r} is a {definition.metric_type.value}, " f"not a {expected.value}"
            )

    def increment(
        self, name: str, value: float = 1.0, *, dimensions: Mapping[str, str] | None = None
    ) -> None:
        """Add ``value`` to a counter."""
        self._check_type(name, MetricType.COUNTER)
        key = self._key(name, dimensions)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def gauge(
        self, name: str, value: float, *, dimensions: Mapping[str, str] | None = None
    ) -> None:
        """Set a gauge to ``value``."""
        self._check_type(name, MetricType.GAUGE)
        key = self._key(name, dimensions)
        with self._lock:
            self._gauges[key] = value

    def observe(
        self, name: str, value: float, *, dimensions: Mapping[str, str] | None = None
    ) -> None:
        """Record a histogram or timer observation."""
        definition = self._catalog.get(name)
        if definition is not None and definition.metric_type not in {
            MetricType.HISTOGRAM,
            MetricType.TIMER,
        }:
            raise MetricError(f"metric {name!r} is not a histogram or timer")
        key = self._key(name, dimensions)
        with self._lock:
            self._histograms.setdefault(key, HistogramValue()).observe(value)

    def snapshot(self) -> dict[str, object]:
        """Return a serialisable snapshot of every recorded metric."""
        with self._lock:
            counters = [
                {"name": key.name, "dimensions": dict(key.dimensions), "value": value}
                for key, value in self._counters.items()
            ]
            gauges = [
                {"name": key.name, "dimensions": dict(key.dimensions), "value": value}
                for key, value in self._gauges.items()
            ]
            histograms = [
                {
                    "name": key.name,
                    "dimensions": dict(key.dimensions),
                    **histogram.summary(min_samples=self._min_samples),
                }
                for key, histogram in self._histograms.items()
            ]
        return {"counters": counters, "gauges": gauges, "histograms": histograms}

    def counter_total(self, name: str) -> float:
        """Return the summed value of a counter across all its dimensions."""
        with self._lock:
            return sum(v for k, v in self._counters.items() if k.name == name)

    def counter_by_dimension(self, name: str, dimension: str) -> dict[str, float]:
        """Return a counter's totals grouped by one dimension's values."""
        totals: dict[str, float] = {}
        with self._lock:
            for key, value in self._counters.items():
                if key.name != name:
                    continue
                label = dict(key.dimensions).get(dimension, "")
                totals[label] = totals.get(label, 0.0) + value
        return totals

    def gauge_value(self, name: str) -> float | None:
        """Return the current value of a gauge, or None if unset."""
        with self._lock:
            for key, value in self._gauges.items():
                if key.name == name:
                    return value
        return None


def catalog_from(definitions: Sequence[MetricDefinition]) -> dict[str, MetricDefinition]:
    """Build a catalog mapping from a sequence of definitions."""
    return {definition.name: definition for definition in definitions}
