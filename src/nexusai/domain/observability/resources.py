"""Models for resource sampling: CPU and memory at a point in time.

A resource sample is a snapshot of the process's CPU time and memory footprint,
taken at a moment. The models are pure; taking the sample is infrastructure,
because it reads the operating system. The distinction the models preserve is
between operating-system memory (resident set size) and Python's own allocation
accounting, which measure different things and must not be conflated.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class ResourceSample:
    """A point-in-time sample of process resource usage.

    Attributes:
        cpu_seconds: Cumulative process CPU time (user + system) in seconds.
        rss_bytes: Resident set size in bytes, as reported by the OS.
        python_allocated_bytes: Current Python-tracked allocation in bytes, when
            allocation tracking is enabled; ``None`` otherwise.
        monotonic_seconds: A monotonic clock reading, for computing deltas.
    """

    cpu_seconds: float
    rss_bytes: int
    python_allocated_bytes: int | None
    monotonic_seconds: float

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {
            "cpu_seconds": self.cpu_seconds,
            "rss_bytes": self.rss_bytes,
            "python_allocated_bytes": self.python_allocated_bytes,
            "monotonic_seconds": self.monotonic_seconds,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ResourceSummary:
    """A summary of resource usage over an interval, computed from two samples.

    Attributes:
        cpu_seconds_used: CPU seconds consumed across the interval.
        wall_seconds: Wall-clock seconds the interval spanned.
        cpu_utilisation: ``cpu_seconds_used / wall_seconds``, a ratio that may
            exceed one on multiple cores; ``None`` when the interval is zero.
        peak_rss_bytes: The larger of the two samples' resident set sizes.
        rss_growth_bytes: End resident set size minus start.
        python_allocated_growth_bytes: Growth in Python-tracked allocation, when
            available.
    """

    cpu_seconds_used: float
    wall_seconds: float
    cpu_utilisation: float | None
    peak_rss_bytes: int
    rss_growth_bytes: int
    python_allocated_growth_bytes: int | None

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {
            "cpu_seconds_used": self.cpu_seconds_used,
            "wall_seconds": self.wall_seconds,
            "cpu_utilisation": self.cpu_utilisation,
            "peak_rss_bytes": self.peak_rss_bytes,
            "rss_growth_bytes": self.rss_growth_bytes,
            "python_allocated_growth_bytes": self.python_allocated_growth_bytes,
        }


def summarise(start: ResourceSample, end: ResourceSample) -> ResourceSummary:
    """Summarise resource usage between two samples."""
    wall = max(0.0, end.monotonic_seconds - start.monotonic_seconds)
    cpu = max(0.0, end.cpu_seconds - start.cpu_seconds)
    utilisation = (cpu / wall) if wall > 0 else None
    py_growth: int | None = None
    if start.python_allocated_bytes is not None and end.python_allocated_bytes is not None:
        py_growth = end.python_allocated_bytes - start.python_allocated_bytes
    return ResourceSummary(
        cpu_seconds_used=cpu,
        wall_seconds=wall,
        cpu_utilisation=utilisation,
        peak_rss_bytes=max(start.rss_bytes, end.rss_bytes),
        rss_growth_bytes=end.rss_bytes - start.rss_bytes,
        python_allocated_growth_bytes=py_growth,
    )
