"""Storage and retrieval of benchmark baselines as JSON files.

A baseline is a saved benchmark result that later runs are compared against. Each
is stored as a JSON document under a baselines directory, keyed by scenario and
size, so a regression check reads a stored baseline rather than a vanished
in-memory run. The format is the result's own ``to_dict`` shape, which keeps the
store trivial and the files human-readable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from nexusai.domain.observability.benchmark import (
    BenchmarkResult,
    EnvironmentFingerprint,
)


class BaselineStore:
    """Reads and writes benchmark baselines under a directory."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def _path(self, scenario: str, size: int) -> Path:
        return self._directory / f"{scenario}.{size}.json"

    def save(self, result: BenchmarkResult) -> Path:
        """Persist ``result`` as the baseline for its scenario and size."""
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self._path(result.scenario, result.size)
        path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        return path

    def load(self, scenario: str, size: int) -> BenchmarkResult | None:
        """Load a stored baseline, or ``None`` if none exists."""
        path = self._path(scenario, size)
        if not path.exists():
            return None
        return _result_from_dict(json.loads(path.read_text(encoding="utf-8")))


def _result_from_dict(data: dict[str, object]) -> BenchmarkResult:
    env = cast("dict[str, object]", data["environment"])
    durations = cast("list[float]", data["durations_seconds"])
    notes = cast("list[str]", data.get("notes", []))
    cpu_count = env["cpu_count"]
    return BenchmarkResult(
        scenario=str(data["scenario"]),
        size=int(cast("int", data["size"])),
        iterations=int(cast("int", data["iterations"])),
        warmup=int(cast("int", data["warmup"])),
        durations_seconds=[float(x) for x in durations],
        records_processed=int(cast("int", data["records_processed"])),
        cpu_seconds=float(cast("float", data["cpu_seconds"])),
        peak_rss_bytes=int(cast("int", data["peak_rss_bytes"])),
        errors=int(cast("int", data["errors"])),
        environment=EnvironmentFingerprint(
            python_version=str(env["python_version"]),
            platform=str(env["platform"]),
            machine=str(env["machine"]),
            cpu_count=int(cast("int", cpu_count)) if cpu_count is not None else None,
            framework_version=str(env["framework_version"]),
            dependencies=cast("dict[str, str]", env.get("dependencies", {})),
        ),
        notes=[str(x) for x in notes],
    )
