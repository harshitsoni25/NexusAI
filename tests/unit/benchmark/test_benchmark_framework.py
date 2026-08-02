"""Tests for the benchmark framework: runner, scenarios, baselines, comparison."""

from __future__ import annotations

from pathlib import Path

from nexusai.application.benchmark.leaks import analyse_leak
from nexusai.application.benchmark.runner import (
    SIZE_TIERS,
    BenchmarkConfig,
    BenchmarkRunner,
)
from nexusai.composition.benchmarks import (
    ALL_SCENARIOS,
    ExtractionScenario,
    ProcessingScenario,
)
from nexusai.domain.observability.benchmark import (
    BenchmarkResult,
    EnvironmentFingerprint,
    RegressionVerdict,
    compare_to_baseline,
)
from nexusai.infrastructure.benchmark.baselines import BaselineStore
from nexusai.infrastructure.benchmark.environment import capture_environment
from nexusai.infrastructure.observability.resources import ResourceSampler


def _runner() -> BenchmarkRunner:
    return BenchmarkRunner(sampler=ResourceSampler(), capture_environment=capture_environment)


class TestRunner:
    def test_runs_iterations_and_measures(self) -> None:
        result = _runner().run(
            ExtractionScenario(), BenchmarkConfig(size=20, iterations=3, warmup=1)
        )
        assert result.scenario == "extraction"
        assert len(result.durations_seconds) == 3
        assert result.records_processed == 20
        assert result.errors == 0
        assert result.median_seconds > 0

    def test_throughput_is_records_over_median(self) -> None:
        result = _runner().run(
            ProcessingScenario(), BenchmarkConfig(size=50, iterations=3, warmup=1)
        )
        throughput = result.throughput_records_per_second
        assert throughput is not None and throughput > 0

    def test_all_scenarios_run_without_error(self) -> None:
        runner = _runner()
        for scenario in ALL_SCENARIOS:
            result = runner.run(scenario, BenchmarkConfig(size=10, iterations=2, warmup=1))
            assert result.errors == 0, f"{scenario.name} had errors"
            assert result.records_processed == 10

    def test_size_tiers_defined(self) -> None:
        assert SIZE_TIERS == {"small": 10, "medium": 100, "large": 1000}


def _result(median: float, *, spread: float = 0.0) -> BenchmarkResult:
    base = median
    durations = [base, base + spread * base, base - spread * base]
    return BenchmarkResult(
        scenario="extraction",
        size=100,
        iterations=3,
        warmup=1,
        durations_seconds=durations,
        records_processed=100,
        cpu_seconds=0.1,
        peak_rss_bytes=1000,
        errors=0,
        environment=capture_environment(),
    )


class TestComparison:
    def test_stable_within_threshold(self) -> None:
        report = compare_to_baseline(_result(1.0), _result(1.02), threshold=0.10)
        assert report.verdict is RegressionVerdict.STABLE

    def test_regression_when_slower(self) -> None:
        report = compare_to_baseline(_result(1.5), _result(1.0), threshold=0.10)
        assert report.verdict is RegressionVerdict.REGRESSION

    def test_improvement_when_faster(self) -> None:
        report = compare_to_baseline(_result(0.5), _result(1.0), threshold=0.10)
        assert report.verdict is RegressionVerdict.IMPROVEMENT

    def test_noisy_small_change_is_inconclusive(self) -> None:
        report = compare_to_baseline(
            _result(1.05, spread=0.5), _result(1.0, spread=0.5), threshold=0.10
        )
        assert report.verdict is RegressionVerdict.INCONCLUSIVE

    def test_environment_mismatch_is_inconclusive(self) -> None:
        current = _result(1.0)
        other_env = EnvironmentFingerprint(
            python_version="2.7.0",
            platform="other",
            machine="arm",
            cpu_count=1,
            framework_version="0.0.0",
        )
        baseline = BenchmarkResult(
            scenario="extraction",
            size=100,
            iterations=3,
            warmup=1,
            durations_seconds=[1.0, 1.0, 1.0],
            records_processed=100,
            cpu_seconds=0.1,
            peak_rss_bytes=1000,
            errors=0,
            environment=other_env,
        )
        report = compare_to_baseline(current, baseline)
        assert report.verdict is RegressionVerdict.INCONCLUSIVE


class TestBaselineStore:
    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        store = BaselineStore(tmp_path)
        result = _runner().run(
            ExtractionScenario(), BenchmarkConfig(size=10, iterations=2, warmup=1)
        )
        path = store.save(result)
        assert path.exists()
        loaded = store.load("extraction", 10)
        assert loaded is not None
        assert loaded.scenario == "extraction"
        assert loaded.records_processed == 10

    def test_load_missing_returns_none(self, tmp_path: Path) -> None:
        assert BaselineStore(tmp_path).load("nope", 10) is None


class TestEnvironment:
    def test_fingerprint_is_self_comparable(self) -> None:
        env = capture_environment()
        assert env.is_comparable_to(env)
        assert env.python_version
        assert "sqlalchemy" in env.dependencies


class TestLeakAnalysis:
    def test_stable_workload_not_suspected(self) -> None:
        report = analyse_leak(lambda: list(range(100)), iterations=10, warmup=2)
        assert report.suspected is False
        assert report.iterations == 10

    def test_growing_workload_is_suspected(self) -> None:
        retained: list[list[int]] = []

        def leaky() -> None:
            retained.append(list(range(20000)))

        report = analyse_leak(leaky, iterations=12, warmup=2, growth_threshold_bytes=100_000)
        assert report.suspected is True
        assert report.growth_bytes > 100_000
