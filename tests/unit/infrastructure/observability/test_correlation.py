"""Task-scoped execution context."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from nexusai.infrastructure.observability.correlation import (
    bind_log_context,
    capture_context,
    correlation_scope,
    current_correlation_id,
    current_log_context,
    restore_context,
)
from nexusai.shared.identifiers import CorrelationId


def test_no_context_by_default() -> None:
    assert current_correlation_id() is None
    assert current_log_context() == {}


def test_a_scope_applies_and_then_reverts() -> None:
    with correlation_scope(CorrelationId("c-1")):
        assert current_correlation_id() == CorrelationId("c-1")
    assert current_correlation_id() is None


def test_scopes_nest_and_unwind_in_order() -> None:
    with correlation_scope(CorrelationId("outer")):
        with correlation_scope(CorrelationId("inner")):
            assert current_correlation_id() == CorrelationId("inner")
        assert current_correlation_id() == CorrelationId("outer")


def test_context_fields_accumulate_rather_than_replace() -> None:
    # A stage inside a site inside a job should produce records carrying all
    # three, without any of them knowing about the others.
    with bind_log_context(job_id="j-1"), bind_log_context(stage="extract"):
        assert current_log_context() == {"job_id": "j-1", "stage": "extract"}
    assert current_log_context() == {}


def test_an_inner_scope_may_shadow_a_field() -> None:
    with bind_log_context(stage="acquire"), bind_log_context(stage="extract"):
        assert current_log_context()["stage"] == "extract"


def test_context_is_isolated_between_concurrent_tasks() -> None:
    # This is the property that makes contextvars acceptable where a global
    # would not be: concurrent work does not observe each other's context.
    async def scenario() -> tuple[str | None, str | None]:
        async def run(name: str, delay: float) -> str | None:
            with correlation_scope(CorrelationId(name)):
                await asyncio.sleep(delay)
                current = current_correlation_id()
                return str(current) if current else None

        first, second = await asyncio.gather(run("a", 0.02), run("b", 0.01))
        return first, second

    assert asyncio.run(scenario()) == ("a", "b")


def test_context_does_not_cross_a_thread_boundary_by_itself() -> None:
    # Documented sharp edge (ADR-0012): asserted so that it stays documented
    # rather than becoming a surprise.
    def read() -> str | None:
        current = current_correlation_id()
        return str(current) if current else None

    with correlation_scope(CorrelationId("c-1")), ThreadPoolExecutor(max_workers=1) as pool:
        assert pool.submit(read).result() is None


def test_capture_and_restore_carry_context_across_a_thread() -> None:
    def read(snapshot: tuple[CorrelationId | None, dict[str, object]]) -> tuple[str | None, object]:
        with restore_context(snapshot):
            current = current_correlation_id()
            return (str(current) if current else None, current_log_context().get("job_id"))

    with correlation_scope(CorrelationId("c-1")), bind_log_context(job_id="j-9"):
        snapshot = capture_context()
        with ThreadPoolExecutor(max_workers=1) as pool:
            assert pool.submit(read, snapshot).result() == ("c-1", "j-9")  # type: ignore[arg-type]
