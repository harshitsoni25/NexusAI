"""The workflow stage contract and its working memory.

A stage is one step of a workflow. It reads the immutable
:class:`~nexusai.application.runtime.context.ExecutionContext` for identities
and references, reads and writes the mutable :class:`Workspace` for the rich
in-flight objects (documents, extraction results, the processed dataset), does
its work by delegating to an engine or service from an earlier phase, and returns
an updated context. It never implements retrieval, extraction, processing,
persistence, export or reporting itself.

The :class:`Workspace` is process-local working memory, deliberately separate
from the context: the context holds small serialisable references that belong on
a job or checkpoint, while the workspace holds large, non-serialisable objects
that live only for the duration of a run. Keeping them apart is what lets the
context stay a clean, persistable snapshot.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from nexusai.application.runtime.context import ExecutionContext


class Workspace:
    """Process-local working memory shared across the stages of one run.

    Stages store and retrieve rich objects here by key. It is a plain in-memory
    holder with no persistence and no serialisation; anything that must outlive
    the run belongs on the context, a checkpoint or a dataset instead.
    """

    def __init__(self) -> None:
        self._items: dict[str, object] = {}

    def put(self, key: str, value: object) -> None:
        """Store ``value`` under ``key``."""
        self._items[key] = value

    def get(self, key: str) -> object | None:
        """Return the value stored under ``key``, or ``None``."""
        return self._items.get(key)

    def require(self, key: str) -> object:
        """Return the value under ``key``, or raise if absent.

        Raises:
            KeyError: If ``key`` has not been set by an earlier stage.
        """
        if key not in self._items:
            raise KeyError(f"workspace is missing required key {key!r}")
        return self._items[key]

    def has(self, key: str) -> bool:
        """Whether ``key`` is present."""
        return key in self._items


@runtime_checkable
class WorkflowStage(Protocol):
    """One step of a workflow, delegating its work to a framework capability."""

    @property
    def name(self) -> str:
        """The stage's identifier, matching a name in the workflow definition."""
        ...

    def can_run(self, context: ExecutionContext, workspace: Workspace) -> bool:
        """Whether this stage's preconditions are met.

        A stage that returns ``False`` is skipped rather than run, which is how an
        optional stage (analysis, export) opts out when it has nothing to do.
        """
        ...

    def execute(self, context: ExecutionContext, workspace: Workspace) -> ExecutionContext:
        """Perform the stage and return the updated context.

        Raises:
            NexusAIError: If the stage's work fails.
        """
        ...
