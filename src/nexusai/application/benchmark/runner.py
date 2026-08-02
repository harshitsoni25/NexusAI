"""The benchmark runner: warm-up, repetition, and honest measurement.

The runner executes a scenario deterministically and repeatedly. It runs a
configurable number of warm-up iterations first -- to pay one-off costs like
imports, JIT-free bytecode caching and connection setup outside the measurement --
then times a configurable number of iterations, recording each duration and the
resource usage across the timed set. It reports the whole distribution, not a
single number, so the median and the spread are both visible and noise cannot hide.

The runner measures; it never optimises and never fabricates. A scenario that
cannot run in this environment returns its own result carrying a note rather than
a made-up timing.
"""

from __future__ import annotations

import gc
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from nexusai.domain.observability.benchmark import BenchmarkResult, EnvironmentFingerprint
from nexusai.domain.ports.observability import ResourceSamplerPort


@runtime_checkable
class BenchmarkScenario(Protocol):
    """A deterministic, repeatable unit of work to be benchmarked."""

    @property
    def name(self) -> str:
        """The scenario's stable name."""
        ...

    def prepare(self, size: int) -> object:
        """Build the fixture for a workload of ``size`` records, once per run."""
        ...

    def execute(self, fixture: object) -> int:
        """Run the timed work against a prepared fixture; return records processed."""
        ...


SIZE_TIERS = {"small": 10, "medium": 100, "large": 1000}
"""The workload size tiers, as explicit record counts."""


@dataclass(frozen=True, slots=True, kw_only=True)
class BenchmarkConfig:
    """How a benchmark is run."""

    size: int = 100
    iterations: int = 5
    warmup: int = 2


class BenchmarkRunner:
    """Runs scenarios with warm-up, repetition and resource sampling."""

    def __init__(
        self,
        *,
        sampler: ResourceSamplerPort,
        capture_environment: Callable[[], EnvironmentFingerprint],
    ) -> None:
        self._sampler = sampler
        self._capture_environment = capture_environment

    def run(self, scenario: BenchmarkScenario, config: BenchmarkConfig) -> BenchmarkResult:
        """Run ``scenario`` under ``config`` and return a measured result."""
        fixture = scenario.prepare(config.size)
        records = 0
        errors = 0

        for _ in range(config.warmup):
            try:
                scenario.execute(fixture)
            except Exception:  # noqa: BLE001 - a warm-up failure is counted, not fatal
                errors += 1

        gc.collect()
        durations: list[float] = []
        start_sample = self._sampler.sample()
        for _ in range(config.iterations):
            begin = time.perf_counter()
            try:
                records = scenario.execute(fixture)
            except Exception:  # noqa: BLE001 - a timed failure is counted honestly
                errors += 1
            durations.append(time.perf_counter() - begin)
        end_sample = self._sampler.sample()

        return BenchmarkResult(
            scenario=scenario.name,
            size=config.size,
            iterations=config.iterations,
            warmup=config.warmup,
            durations_seconds=durations,
            records_processed=records,
            cpu_seconds=max(0.0, end_sample.cpu_seconds - start_sample.cpu_seconds),
            peak_rss_bytes=max(start_sample.rss_bytes, end_sample.rss_bytes),
            errors=errors,
            environment=self._capture_environment(),
        )
