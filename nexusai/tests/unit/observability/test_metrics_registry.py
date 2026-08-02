"""Tests for the vendor-neutral metrics registry and its governance."""

from __future__ import annotations

import threading
from typing import cast

import pytest

from nexusai.domain.observability.metrics import (
    MetricDefinition,
    MetricType,
    MetricUnit,
    Outcome,
    is_valid_metric_name,
)
from nexusai.infrastructure.observability.registry import (
    MetricError,
    MetricsRegistry,
    catalog_from,
)


def _catalog() -> dict[str, MetricDefinition]:
    return catalog_from(
        [
            MetricDefinition(
                name="nexusai.request.attempted",
                metric_type=MetricType.COUNTER,
                unit=MetricUnit.COUNT,
                description="Requests attempted.",
                dimensions=("outcome",),
            ),
            MetricDefinition(
                name="nexusai.active.jobs",
                metric_type=MetricType.GAUGE,
                unit=MetricUnit.COUNT,
                description="Active jobs.",
            ),
            MetricDefinition(
                name="nexusai.request.duration",
                metric_type=MetricType.TIMER,
                unit=MetricUnit.SECONDS,
                description="Request duration.",
            ),
        ]
    )


class TestNaming:
    @pytest.mark.parametrize("name", ["nexusai.job.completed", "a.b", "x.y.z"])
    def test_valid_names(self, name: str) -> None:
        assert is_valid_metric_name(name)

    @pytest.mark.parametrize("name", ["Job", "job", "Job.Completed", "job..completed", "1.x"])
    def test_invalid_names(self, name: str) -> None:
        assert not is_valid_metric_name(name)


class TestCounters:
    def test_increment_and_total(self) -> None:
        reg = MetricsRegistry(_catalog())
        reg.increment("nexusai.request.attempted", dimensions={"outcome": "success"})
        reg.increment("nexusai.request.attempted", 2, dimensions={"outcome": "success"})
        reg.increment("nexusai.request.attempted", dimensions={"outcome": "failure"})
        assert reg.counter_total("nexusai.request.attempted") == 4
        by_outcome = reg.counter_by_dimension("nexusai.request.attempted", "outcome")
        assert by_outcome == {"success": 3.0, "failure": 1.0}


class TestGauges:
    def test_gauge_last_write_wins(self) -> None:
        reg = MetricsRegistry(_catalog())
        reg.gauge("nexusai.active.jobs", 3)
        reg.gauge("nexusai.active.jobs", 5)
        assert reg.gauge_value("nexusai.active.jobs") == 5


class TestHistogram:
    def test_percentiles_require_enough_samples(self) -> None:
        reg = MetricsRegistry(_catalog(), min_samples=20)
        for _ in range(5):
            reg.observe("nexusai.request.duration", 0.1)
        histograms = cast("list[dict[str, object]]", reg.snapshot()["histograms"])
        summary = next(h for h in histograms if h["name"] == "nexusai.request.duration")
        assert summary["percentiles_reliable"] is False
        assert summary["p95"] is None

    def test_percentiles_reported_when_sufficient(self) -> None:
        reg = MetricsRegistry(_catalog(), min_samples=20)
        for i in range(30):
            reg.observe("nexusai.request.duration", float(i))
        histograms = cast("list[dict[str, object]]", reg.snapshot()["histograms"])
        summary = next(h for h in histograms if h["name"] == "nexusai.request.duration")
        assert summary["percentiles_reliable"] is True
        assert summary["p50"] is not None


class TestCardinalityGovernance:
    def test_unknown_dimension_rejected(self) -> None:
        reg = MetricsRegistry(_catalog())
        with pytest.raises(MetricError):
            reg.increment("nexusai.request.attempted", dimensions={"url": "https://x"})

    def test_invalid_name_rejected(self) -> None:
        with pytest.raises(MetricError):
            MetricsRegistry(_catalog()).increment("BadName")

    def test_overlong_dimension_value_rejected(self) -> None:
        reg = MetricsRegistry(_catalog())
        with pytest.raises(MetricError):
            reg.increment("nexusai.request.attempted", dimensions={"outcome": "x" * 65})

    def test_wrong_type_rejected(self) -> None:
        reg = MetricsRegistry(_catalog())
        with pytest.raises(MetricError):
            reg.gauge("nexusai.request.attempted", 1)


class TestConcurrency:
    def test_concurrent_increments_are_not_lost(self) -> None:
        reg = MetricsRegistry(_catalog())

        def work() -> None:
            for _ in range(1000):
                reg.increment("nexusai.request.attempted", dimensions={"outcome": "success"})

        threads = [threading.Thread(target=work) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert reg.counter_total("nexusai.request.attempted") == 4000


class TestOutcomeTaxonomy:
    def test_all_outcomes_have_stable_values(self) -> None:
        assert Outcome.SUCCESS.value == "success"
        assert {o.value for o in Outcome} == {
            "success",
            "warning",
            "partial",
            "failure",
            "cancelled",
            "skipped",
            "retried",
        }
