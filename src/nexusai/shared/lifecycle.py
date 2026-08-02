"""Generic object lifecycle: creation, initialisation, disposal.

Many framework components acquire resources when a run begins and release them
when it ends -- plugins, strategies, storage providers, exporters. Rather than
each inventing its own initialise/dispose convention, they share the protocols
here.

These are pure and dependency-free, so any layer may use them without creating a
cross-layer dependency. That matters: an infrastructure adapter and an
application service both need lifecycle, and neither may import the other.
"""

from __future__ import annotations

from enum import Enum
from typing import Protocol, runtime_checkable


class LifecycleState(Enum):
    """The stage a lifecycle-aware component is in.

    The progression is linear and one-way: a disposed component is not
    reinitialised. Recreate it instead. Tracking the state is what lets a
    manager skip double-initialisation and make disposal idempotent.
    """

    CREATED = "created"
    INITIALISED = "initialised"
    DISPOSED = "disposed"


@runtime_checkable
class Initializable(Protocol):
    """A component that acquires resources before use."""

    def initialize(self) -> None:
        """Acquire resources. Called once, before the component is used.

        Construction must stay cheap and side-effect free; all resource
        acquisition belongs here. That separation is what lets a component be
        created for inspection -- to read its metadata, say -- without opening a
        file or a connection.
        """
        ...


@runtime_checkable
class Disposable(Protocol):
    """A component that releases resources when it is finished with."""

    def dispose(self) -> None:
        """Release resources. Called once, when the component is finished with.

        Must be safe to call even if initialisation failed or never ran, and
        must not raise: a disposal failure is logged, never allowed to mask the
        outcome of the work the component was doing.
        """
        ...


@runtime_checkable
class LifecycleAware(Initializable, Disposable, Protocol):
    """A component with both an initialisation and a disposal phase."""


class LifecycleMixin:
    """Default no-op lifecycle plus state tracking, for components that want it.

    Optional. A component may implement the protocols directly instead. This
    mixin exists only to spare the common case -- a component with nothing to
    dispose -- from writing two empty methods, while still tracking state so a
    manager can reason about it.

    Composition is still preferred where a component already has a natural base;
    this is a convenience, not a mandated hierarchy.
    """

    __slots__ = ("_lifecycle_state",)

    _lifecycle_state: LifecycleState

    def __init__(self) -> None:
        self._lifecycle_state = LifecycleState.CREATED

    @property
    def lifecycle_state(self) -> LifecycleState:
        """The stage this component has reached."""
        return getattr(self, "_lifecycle_state", LifecycleState.CREATED)

    def initialize(self) -> None:
        """Advance to the initialised state. Override to acquire resources."""
        self._lifecycle_state = LifecycleState.INITIALISED

    def dispose(self) -> None:
        """Advance to the disposed state. Override to release resources.

        Idempotent: disposing an already-disposed or never-initialised component
        does nothing.
        """
        self._lifecycle_state = LifecycleState.DISPOSED
