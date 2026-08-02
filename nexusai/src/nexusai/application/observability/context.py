"""Execution-safe propagation of observability identity.

The observability context carries the identifiers that stitch a log line, a
metric and a timeline event back to the same unit of work -- correlation, run,
job, workflow, stage, operation and target. It is propagated through
:class:`contextvars.ContextVar`, which is execution-safe and, crucially for this
synchronous, threaded framework, isolated per thread: two concurrent jobs on two
threads each see their own context, with no shared mutable global.

Identifiers here are always safe to log and to use as bounded metric dimensions.
A secret is never an identifier; the context holds correlation ids and stage
names, never tokens or credentials.
"""

from __future__ import annotations

import contextvars
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True, kw_only=True)
class ObservabilityContext:
    """The identity of the current unit of work, for logs, metrics and timeline.

    Attributes:
        correlation_id: Ties together everything in one logical operation.
        run_id: The run this belongs to, when applicable.
        job_id: The job being executed.
        workflow_version: The workflow definition version.
        stage: The stage currently executing.
        operation: The fine-grained operation currently executing.
        target: The site or target identifier (never a full URL with secrets).
        dataset_id: The dataset being produced.
    """

    correlation_id: str | None = None
    run_id: str | None = None
    job_id: str | None = None
    workflow_version: str | None = None
    stage: str | None = None
    operation: str | None = None
    target: str | None = None
    dataset_id: str | None = None

    def as_log_fields(self) -> dict[str, str]:
        """Return the non-empty identifiers as structured log fields."""
        fields: dict[str, str] = {}
        for name, value in {
            "correlation_id": self.correlation_id,
            "run_id": self.run_id,
            "job_id": self.job_id,
            "workflow_version": self.workflow_version,
            "stage": self.stage,
            "operation": self.operation,
            "target": self.target,
            "dataset_id": self.dataset_id,
        }.items():
            if value is not None:
                fields[name] = value
        return fields


_EMPTY = ObservabilityContext()
_CURRENT: contextvars.ContextVar[ObservabilityContext | None] = contextvars.ContextVar(
    "nexusai_observability_context", default=None
)


def current_context() -> ObservabilityContext:
    """Return the observability context of the current execution."""
    return _CURRENT.get() or _EMPTY


@contextmanager
def observability_scope(**changes: str | None) -> Iterator[ObservabilityContext]:
    """Enter a nested scope with the given identifiers set on the context.

    The change is visible only within the ``with`` block and only within the
    current execution (thread and any code it calls synchronously); on exit the
    previous context is restored. Nested scopes merge with the enclosing one.
    """
    updated = replace(current_context(), **changes)
    token = _CURRENT.set(updated)
    try:
        yield updated
    finally:
        _CURRENT.reset(token)


def bind_context(
    context: ObservabilityContext,
) -> contextvars.Token[ObservabilityContext | None]:
    """Set the current context wholesale, returning a token to restore it."""
    return _CURRENT.set(context)


def reset_context(token: contextvars.Token[ObservabilityContext | None]) -> None:
    """Restore the context to the state captured by ``token``."""
    _CURRENT.reset(token)


def merged_dimensions(
    base: Mapping[str, str] | None = None, *, allowed: frozenset[str] = frozenset()
) -> dict[str, str]:
    """Merge explicit dimensions with context identifiers permitted as labels.

    Only identifiers named in ``allowed`` are drawn from the context, keeping
    metric cardinality bounded; everything else stays in logs and the timeline.
    """
    result: dict[str, str] = dict(base or {})
    context_fields = current_context().as_log_fields()
    for name in allowed:
        if name in context_fields and name not in result:
            result[name] = context_fields[name]
    return result
