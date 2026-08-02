"""Metric sinks."""

from __future__ import annotations

from nexusai.infrastructure.observability.metrics import InMemoryMetricsSink, NullMetricsSink


def test_the_null_sink_accepts_everything_and_keeps_nothing() -> None:
    sink = NullMetricsSink()
    sink.increment("pages")
    sink.gauge("memory", 1.0)
    sink.timing("run", 2.0)


def test_counters_accumulate() -> None:
    sink = InMemoryMetricsSink()
    sink.increment("pages")
    sink.increment("pages", 4)
    assert sink.counters["pages"] == 5


def test_tags_keep_counters_distinct() -> None:
    sink = InMemoryMetricsSink()
    sink.increment("pages", tags={"site": "a"})
    sink.increment("pages", tags={"site": "b"})
    assert sink.counters["pages[site=a]"] == 1
    assert sink.counters["pages[site=b]"] == 1


def test_tag_order_does_not_create_separate_counters() -> None:
    sink = InMemoryMetricsSink()
    sink.increment("pages", tags={"site": "a", "stage": "x"})
    sink.increment("pages", tags={"stage": "x", "site": "a"})
    assert len(sink.counters) == 1


def test_gauges_and_timings_are_recorded_in_order() -> None:
    sink = InMemoryMetricsSink()
    sink.gauge("memory", 1.5)
    sink.timing("run", 0.25)
    sink.timing("run", 0.75)
    assert sink.gauges[0].value == 1.5
    assert list(sink.timings_for("run")) == [0.25, 0.75]


def test_the_snapshot_is_serialisable() -> None:
    sink = InMemoryMetricsSink()
    sink.increment("pages")
    sink.gauge("memory", 2.0, tags={"host": "a"})
    snapshot = sink.snapshot()
    assert snapshot["counters"] == {"pages": 1}
    assert snapshot["gauges"] == [("memory", 2.0, {"host": "a"})]
