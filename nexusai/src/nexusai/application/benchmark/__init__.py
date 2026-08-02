"""Deterministic benchmarking: runner, scenarios, leak analysis.

Holds the benchmark runner (warm-up, repetition, resource sampling), the
fixture-based scenarios that exercise each pipeline stage, and the repeated-
workload leak analyser. Comparison against baselines and the environment
fingerprint live in the domain and infrastructure respectively.
"""

from __future__ import annotations

from nexusai.application.benchmark.leaks import LeakReport, analyse_leak
from nexusai.application.benchmark.runner import (
    SIZE_TIERS,
    BenchmarkConfig,
    BenchmarkRunner,
    BenchmarkScenario,
)

__all__ = [
    "SIZE_TIERS",
    "BenchmarkConfig",
    "BenchmarkRunner",
    "BenchmarkScenario",
    "LeakReport",
    "analyse_leak",
]
