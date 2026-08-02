"""Benchmark infrastructure: environment capture and baseline storage.

Holds the environment fingerprint capture (which reads the machine and dependency
versions) and the baseline store (which persists and retrieves benchmark results
as JSON), keeping the benchmark runner and comparison logic free of I/O.
"""

from __future__ import annotations

from nexusai.infrastructure.benchmark.baselines import BaselineStore
from nexusai.infrastructure.benchmark.environment import capture_environment

__all__ = ["BaselineStore", "capture_environment"]
