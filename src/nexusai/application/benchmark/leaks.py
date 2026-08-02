"""Resource-leak analysis over repeated workloads.

A leak shows up not in one run but across many: memory that grows monotonically as
the same bounded workload repeats is the signature of an object retained that
should have been released. This analyser runs a scenario a fixed number of times,
sampling Python-tracked allocation between runs, and reports whether the trend is
flat (healthy) or rising (suspicious), along with the growth observed.

It reports a suspicion, not a verdict. Allocation can drift for benign reasons --
caches warming, interned strings -- so the analyser flags a *sustained* upward
trend past a threshold and leaves the confirmation to a human, rather than crying
leak at the first wobble.
"""

from __future__ import annotations

import gc
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class LeakReport:
    """The outcome of a repeated-workload leak analysis.

    Attributes:
        iterations: How many times the workload ran.
        samples_bytes: Python-tracked allocation after each iteration.
        growth_bytes: Allocation at the end minus the start.
        suspected: Whether a sustained upward trend past the threshold was seen.
        detail: A short human-readable summary.
    """

    iterations: int
    samples_bytes: tuple[int, ...]
    growth_bytes: int
    suspected: bool
    detail: str

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {
            "iterations": self.iterations,
            "samples_bytes": list(self.samples_bytes),
            "growth_bytes": self.growth_bytes,
            "suspected": self.suspected,
            "detail": self.detail,
        }


def analyse_leak(
    workload: Callable[[], object],
    *,
    iterations: int = 20,
    warmup: int = 3,
    growth_threshold_bytes: int = 1_000_000,
) -> LeakReport:
    """Run ``workload`` repeatedly and report whether memory grows suspiciously.

    Args:
        workload: A callable performing one unit of the repeated work.
        iterations: How many measured iterations to run.
        warmup: Iterations to run before measuring, so caches settle.
        growth_threshold_bytes: Sustained growth above this is flagged.
    """
    started_here = not tracemalloc.is_tracing()
    if started_here:
        tracemalloc.start()

    for _ in range(warmup):
        workload()
    gc.collect()

    samples: list[int] = []
    for _ in range(iterations):
        workload()
        gc.collect()
        samples.append(tracemalloc.get_traced_memory()[0])

    if started_here:
        tracemalloc.stop()

    growth = samples[-1] - samples[0] if samples else 0
    # A sustained trend: the second half is consistently above the first half.
    half = len(samples) // 2
    first_avg = sum(samples[:half]) / half if half else 0
    second_avg = sum(samples[half:]) / (len(samples) - half) if samples else 0
    sustained = second_avg > first_avg and growth > growth_threshold_bytes
    detail = f"allocation grew {growth} bytes over {iterations} iterations; " + (
        "sustained upward trend — investigate" if sustained else "trend is flat/benign"
    )
    return LeakReport(
        iterations=iterations,
        samples_bytes=tuple(samples),
        growth_bytes=growth,
        suspected=sustained,
        detail=detail,
    )
