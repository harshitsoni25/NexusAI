"""Pure models for benchmarking: results, environment, and regression verdicts.

A benchmark result is a measured, reproducible record: which scenario ran, at what
size, how many times, how long each run took, and what resources it used -- stamped
with an environment fingerprint so a number is never compared across incomparable
machines. The models are pure values; running the benchmark and reading the
machine are the layers above.

Comparison is explicit and honest. A regression verdict distinguishes a genuine
regression from noise and from an inconclusive comparison (too few samples, or an
environment mismatch), so a small run never masquerades as a confident result.
"""

from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True, slots=True, kw_only=True)
class EnvironmentFingerprint:
    """The environment a benchmark ran in, for comparability.

    Attributes:
        python_version: The interpreter version.
        platform: The operating system and release.
        machine: The CPU architecture.
        cpu_count: The number of CPUs available.
        framework_version: The Nexus AI version.
        dependencies: Versions of relevant dependencies.
    """

    python_version: str
    platform: str
    machine: str
    cpu_count: int | None
    framework_version: str
    dependencies: Mapping[str, str] = field(default_factory=dict)

    def is_comparable_to(self, other: EnvironmentFingerprint) -> bool:
        """Whether two fingerprints are alike enough to compare results."""
        return (
            self.python_version == other.python_version
            and self.platform == other.platform
            and self.machine == other.machine
            and self.framework_version == other.framework_version
        )

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {
            "python_version": self.python_version,
            "platform": self.platform,
            "machine": self.machine,
            "cpu_count": self.cpu_count,
            "framework_version": self.framework_version,
            "dependencies": dict(self.dependencies),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class BenchmarkResult:
    """The measured outcome of running one benchmark scenario.

    Attributes:
        scenario: The scenario's name.
        size: The workload size tier (records processed per iteration).
        iterations: How many timed iterations were run.
        warmup: How many warm-up iterations preceded them.
        durations_seconds: The per-iteration wall-clock durations.
        records_processed: Records processed per iteration.
        cpu_seconds: CPU seconds consumed across the timed iterations.
        peak_rss_bytes: Peak resident set size observed.
        errors: Errors encountered during timed iterations.
        environment: The environment fingerprint.
        notes: Any caveats (for example, a NOT VERIFIED marker).
    """

    scenario: str
    size: int
    iterations: int
    warmup: int
    durations_seconds: Sequence[float]
    records_processed: int
    cpu_seconds: float
    peak_rss_bytes: int
    errors: int
    environment: EnvironmentFingerprint
    notes: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "durations_seconds", tuple(self.durations_seconds))
        object.__setattr__(self, "notes", tuple(self.notes))

    @property
    def median_seconds(self) -> float:
        """The median per-iteration duration, a stable central measure."""
        return statistics.median(self.durations_seconds) if self.durations_seconds else 0.0

    @property
    def throughput_records_per_second(self) -> float | None:
        """Records processed per second at the median duration, when meaningful."""
        median = self.median_seconds
        if median <= 0 or self.records_processed <= 0:
            return None
        return self.records_processed / median

    @property
    def spread_ratio(self) -> float | None:
        """The ratio of the duration range to the median, a noise indicator."""
        if not self.durations_seconds or self.median_seconds <= 0:
            return None
        return (max(self.durations_seconds) - min(self.durations_seconds)) / self.median_seconds

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {
            "scenario": self.scenario,
            "size": self.size,
            "iterations": self.iterations,
            "warmup": self.warmup,
            "durations_seconds": list(self.durations_seconds),
            "median_seconds": self.median_seconds,
            "throughput_records_per_second": self.throughput_records_per_second,
            "spread_ratio": self.spread_ratio,
            "records_processed": self.records_processed,
            "cpu_seconds": self.cpu_seconds,
            "peak_rss_bytes": self.peak_rss_bytes,
            "errors": self.errors,
            "environment": self.environment.to_dict(),
            "notes": list(self.notes),
        }


class RegressionVerdict(Enum):
    """The verdict of comparing a result against a baseline."""

    IMPROVEMENT = "improvement"
    STABLE = "stable"
    REGRESSION = "regression"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True, slots=True, kw_only=True)
class RegressionReport:
    """The outcome of comparing a benchmark result against a baseline."""

    scenario: str
    verdict: RegressionVerdict
    baseline_median: float
    current_median: float
    change_ratio: float
    detail: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {
            "scenario": self.scenario,
            "verdict": self.verdict.value,
            "baseline_median": self.baseline_median,
            "current_median": self.current_median,
            "change_ratio": self.change_ratio,
            "detail": self.detail,
        }


def compare_to_baseline(
    current: BenchmarkResult,
    baseline: BenchmarkResult,
    *,
    threshold: float = 0.10,
) -> RegressionReport:
    """Compare a result to a baseline, distinguishing signal from noise.

    A change smaller than ``threshold`` is stable; a slowdown beyond it is a
    regression and a speed-up an improvement. The comparison is inconclusive when
    the environments differ or either run is too noisy (spread exceeds the
    threshold), so noise is never reported as a regression.
    """
    baseline_median = baseline.median_seconds
    current_median = current.median_seconds
    if baseline_median <= 0 or current_median <= 0:
        return _report(current, baseline, RegressionVerdict.INCONCLUSIVE, 0.0, "no baseline timing")
    if not current.environment.is_comparable_to(baseline.environment):
        return _report(
            current, baseline, RegressionVerdict.INCONCLUSIVE, 0.0, "environment mismatch"
        )
    change = (current_median - baseline_median) / baseline_median
    noisy = (current.spread_ratio or 0.0) > threshold or (baseline.spread_ratio or 0.0) > threshold
    if noisy and abs(change) < threshold * 2:
        return _report(current, baseline, RegressionVerdict.INCONCLUSIVE, change, "within noise")
    if change > threshold:
        return _report(
            current, baseline, RegressionVerdict.REGRESSION, change, "slower than baseline"
        )
    if change < -threshold:
        return _report(
            current, baseline, RegressionVerdict.IMPROVEMENT, change, "faster than baseline"
        )
    return _report(current, baseline, RegressionVerdict.STABLE, change, "within threshold")


def _report(
    current: BenchmarkResult,
    baseline: BenchmarkResult,
    verdict: RegressionVerdict,
    change: float,
    detail: str,
) -> RegressionReport:
    return RegressionReport(
        scenario=current.scenario,
        verdict=verdict,
        baseline_median=baseline.median_seconds,
        current_median=current.median_seconds,
        change_ratio=change,
        detail=detail,
    )
