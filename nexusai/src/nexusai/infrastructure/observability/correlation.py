"""Task-scoped execution context for logs, metrics and events.

Correlation identity is held in :mod:`contextvars` rather than passed through
every function signature. The alternative -- threading an identifier through
every call -- would pollute every interface in the framework for the benefit of
one cross-cutting concern.

``ContextVar`` is task-scoped rather than process-global, so it does not
constitute the shared mutable global state that section 8 of the Master
Specification prohibits: concurrent tasks observe independent values, and a
value set inside a scope is discarded when the scope exits.

The known sharp edge is propagation into worker threads and executors, which is
not automatic. :func:`capture_context` and :func:`restore_context` exist for
that case and are exercised by the test suite (ADR-0012).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from nexusai.shared.identifiers import CorrelationId

_EMPTY: Mapping[str, Any] = {}

_correlation_id: ContextVar[CorrelationId | None] = ContextVar(
    "nexusai_correlation_id", default=None
)
_log_context: ContextVar[Mapping[str, Any]] = ContextVar("nexusai_log_context", default=_EMPTY)


def current_correlation_id() -> CorrelationId | None:
    """Return the correlation identifier of the running execution, if any."""
    return _correlation_id.get()


def current_log_context() -> Mapping[str, Any]:
    """Return the contextual fields attached to the running execution."""
    return _log_context.get()


@contextmanager
def correlation_scope(correlation_id: CorrelationId) -> Iterator[CorrelationId]:
    """Attach ``correlation_id`` to everything logged inside the block.

    Yields:
        The correlation identifier now in effect.
    """
    token = _correlation_id.set(correlation_id)
    try:
        yield correlation_id
    finally:
        _correlation_id.reset(token)


@contextmanager
def bind_log_context(**fields: Any) -> Iterator[Mapping[str, Any]]:
    """Attach ``fields`` to everything logged inside the block.

    Fields accumulate: an inner scope adds to the outer scope's fields rather
    than replacing them, so a stage nested inside a site inside a job produces
    log records carrying all three.

    Yields:
        The merged context now in effect.
    """
    merged: Mapping[str, Any] = {**_log_context.get(), **fields}
    token = _log_context.set(merged)
    try:
        yield merged
    finally:
        _log_context.reset(token)


def capture_context() -> tuple[CorrelationId | None, Mapping[str, Any]]:
    """Snapshot the current context for transfer to another thread.

    ``contextvars`` does not cross a thread or executor boundary by itself. Work
    handed to a thread pool must capture the context here and restore it on the
    receiving side.
    """
    return _correlation_id.get(), _log_context.get()


@contextmanager
def restore_context(
    snapshot: tuple[CorrelationId | None, Mapping[str, Any]],
) -> Iterator[None]:
    """Re-establish a context captured by :func:`capture_context`."""
    correlation_id, context = snapshot
    correlation_token = _correlation_id.set(correlation_id)
    context_token = _log_context.set(context)
    try:
        yield
    finally:
        _log_context.reset(context_token)
        _correlation_id.reset(correlation_token)
