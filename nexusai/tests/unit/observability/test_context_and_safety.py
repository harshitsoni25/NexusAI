"""Tests for observability context propagation, isolation, and failure isolation."""

from __future__ import annotations

import threading

from nexusai.application.observability.context import (
    ObservabilityContext,
    current_context,
    merged_dimensions,
    observability_scope,
)
from nexusai.application.observability.safety import safely
from nexusai.testing import RecordingLogger


class TestContextPropagation:
    def test_default_is_empty(self) -> None:
        assert current_context().as_log_fields() == {}

    def test_scope_sets_and_restores(self) -> None:
        with observability_scope(job_id="j1", correlation_id="c1"):
            assert current_context().job_id == "j1"
        assert current_context().job_id is None

    def test_nested_scopes_merge(self) -> None:
        with observability_scope(job_id="j1"), observability_scope(stage="retrieve"):
            fields = current_context().as_log_fields()
            assert fields == {"job_id": "j1", "stage": "retrieve"}

    def test_as_log_fields_omits_empty(self) -> None:
        context = ObservabilityContext(job_id="j1")
        assert context.as_log_fields() == {"job_id": "j1"}


class TestThreadIsolation:
    def test_threads_have_independent_contexts(self) -> None:
        seen: dict[str, str | None] = {}

        def worker() -> None:
            with observability_scope(job_id="worker"):
                seen["worker"] = current_context().job_id

        with observability_scope(job_id="main"):
            thread = threading.Thread(target=worker)
            thread.start()
            thread.join()
            seen["main"] = current_context().job_id

        assert seen == {"main": "main", "worker": "worker"}

    def test_worker_does_not_see_main_scope(self) -> None:
        seen: dict[str, str | None] = {}

        def worker() -> None:
            seen["worker"] = current_context().job_id

        with observability_scope(job_id="main"):
            thread = threading.Thread(target=worker)
            thread.start()
            thread.join()
        assert seen["worker"] is None


class TestMergedDimensions:
    def test_only_allowed_context_fields_become_dimensions(self) -> None:
        with observability_scope(job_id="j1", target="site", correlation_id="c1"):
            dimensions = merged_dimensions({"outcome": "success"}, allowed=frozenset({"target"}))
        assert dimensions == {"outcome": "success", "target": "site"}

    def test_explicit_dimensions_win(self) -> None:
        with observability_scope(target="from-context"):
            dimensions = merged_dimensions({"target": "explicit"}, allowed=frozenset({"target"}))
        assert dimensions["target"] == "explicit"


class TestFailureIsolation:
    def test_safely_swallows_and_warns(self) -> None:
        logger = RecordingLogger()

        def boom() -> None:
            raise RuntimeError("collector down")

        with safely("metric.record", logger=logger):
            boom()
        assert any(record.message == "observability.suppressed" for record in logger.records)

    def test_safely_silent_without_logger(self) -> None:
        def boom() -> None:
            raise ValueError("boom")

        with safely("metric.record"):
            boom()

    def test_safely_allows_success(self) -> None:
        result = []
        with safely("metric.record"):
            result.append(1)
        assert result == [1]
