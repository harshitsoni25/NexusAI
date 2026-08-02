"""Tests for timing instrumentation and resource sampling."""

from __future__ import annotations

import pytest

from nexusai.application.observability.instrumentation import timed, timer
from nexusai.domain.observability.resources import ResourceSample, summarise
from nexusai.infrastructure.observability.resources import ResourceSampler
from nexusai.testing import FrozenClock


class TestTimer:
    def test_records_duration(self) -> None:
        recorded: list[tuple[str, float]] = []
        clock = FrozenClock()
        with timer(clock, lambda n, s, d: recorded.append((n, s)), "nexusai.stage.duration"):
            pass
        assert recorded and recorded[0][0] == "nexusai.stage.duration"

    def test_records_even_when_body_raises(self) -> None:
        recorded: list[float] = []
        clock = FrozenClock()
        with (
            pytest.raises(ValueError, match="boom"),
            timer(clock, lambda n, s, d: recorded.append(s), "nexusai.stage.duration"),
        ):
            raise ValueError("boom")
        assert len(recorded) == 1

    def test_recording_failure_does_not_propagate(self) -> None:
        clock = FrozenClock()

        def bad(name: str, seconds: float, dims: object) -> None:
            raise RuntimeError("sink down")

        with timer(clock, bad, "nexusai.stage.duration"):
            pass  # must not raise

    def test_timed_decorator(self) -> None:
        recorded: list[str] = []
        clock = FrozenClock()

        @timed(clock, lambda n, s, d: recorded.append(n), "nexusai.stage.duration")
        def work() -> int:
            return 42

        assert work() == 42
        assert recorded == ["nexusai.stage.duration"]


class TestResourceSampling:
    def test_sample_has_nonnegative_readings(self) -> None:
        sample = ResourceSampler().sample()
        assert sample.cpu_seconds >= 0
        assert sample.rss_bytes > 0

    def test_cpu_count_is_available(self) -> None:
        count = ResourceSampler().cpu_count
        assert count is None or count >= 1

    def test_summarise_computes_deltas(self) -> None:
        start = ResourceSample(
            cpu_seconds=1.0, rss_bytes=1000, python_allocated_bytes=100, monotonic_seconds=0.0
        )
        end = ResourceSample(
            cpu_seconds=1.5, rss_bytes=1500, python_allocated_bytes=300, monotonic_seconds=2.0
        )
        summary = summarise(start, end)
        assert summary.cpu_seconds_used == 0.5
        assert summary.wall_seconds == 2.0
        assert summary.cpu_utilisation == 0.25
        assert summary.rss_growth_bytes == 500
        assert summary.python_allocated_growth_bytes == 200

    def test_summarise_zero_interval_has_no_utilisation(self) -> None:
        s = ResourceSample(
            cpu_seconds=1.0, rss_bytes=1000, python_allocated_bytes=None, monotonic_seconds=5.0
        )
        summary = summarise(s, s)
        assert summary.cpu_utilisation is None
        assert summary.python_allocated_growth_bytes is None
