"""Reusable base classes for framework services.

Provided because they remove real duplication: nearly every service needs a name,
a context, and lifecycle methods, and writing those by hand each time is noise.
This is the one place the SDK offers inheritance, and it does so for a component
kind the application layer owns -- so it creates no cross-layer dependency, unlike
a base class that infrastructure would extend.

For the contract-implementing components that infrastructure provides -- exporters,
storage providers, repositories -- the SDK deliberately ships no base class.
Those implement their Protocol directly and compose in ``LifecycleMixin`` if they
want default lifecycle. Protocols were chosen over abstract bases precisely so an
adapter need not inherit from the framework (ADR-0003), and a base class it had to
import would undo that.
"""

from __future__ import annotations

from collections.abc import Sequence

from nexusai.domain.model.context import FrameworkContext
from nexusai.shared.lifecycle import LifecycleState


class BaseService:
    """A framework service with a name, a context and default lifecycle.

    Subclasses override :meth:`on_initialize` and :meth:`on_dispose` rather than
    the public lifecycle methods, so that state tracking and idempotency are
    handled once, here, and cannot be forgotten by a subclass.

    Args:
        name: Stable identifier for logs, metrics and diagnostics.
        context: Ambient collaborators, with the logger already bound to ``name``.
    """

    __slots__ = ("_context", "_name", "_state")

    def __init__(self, name: str, context: FrameworkContext) -> None:
        self._name = name
        self._context = context.for_component(name)
        self._state = LifecycleState.CREATED

    @property
    def name(self) -> str:
        """The service's stable identifier."""
        return self._name

    @property
    def context(self) -> FrameworkContext:
        """The service's ambient context, logger bound to its name."""
        return self._context

    @property
    def lifecycle_state(self) -> LifecycleState:
        """The stage this service has reached."""
        return self._state

    def initialize(self) -> None:
        """Initialise the service exactly once.

        Calling twice is a no-op rather than an error, so that a manager need not
        track which services it has already started.
        """
        if self._state is not LifecycleState.CREATED:
            return
        self.on_initialize()
        self._state = LifecycleState.INITIALISED

    def dispose(self) -> None:
        """Dispose the service exactly once. Safe before initialisation."""
        if self._state is LifecycleState.DISPOSED:
            return
        self.on_dispose()
        self._state = LifecycleState.DISPOSED

    def on_initialize(self) -> None:
        """Acquire resources. Override in a subclass that needs to."""

    def on_dispose(self) -> None:
        """Release resources. Override in a subclass that needs to."""


class CompositeService(BaseService):
    """A service composed of ordered child services.

    Initialises its children in order and disposes them in reverse, so that a
    child which depends on an earlier sibling is initialised after it and torn
    down before it. This expresses composition directly: a larger service is
    built by combining smaller ones rather than by deepening an inheritance
    hierarchy.

    A child that fails to dispose does not prevent its siblings from being
    disposed; the failure surfaces through the manager, not by leaking resources.
    """

    __slots__ = ("_children",)

    def __init__(
        self, name: str, context: FrameworkContext, children: Sequence[BaseService]
    ) -> None:
        super().__init__(name, context)
        self._children = tuple(children)

    @property
    def children(self) -> tuple[BaseService, ...]:
        """The child services, in initialisation order."""
        return self._children

    def on_initialize(self) -> None:
        """Initialise each child in order."""
        for child in self._children:
            child.initialize()

    def on_dispose(self) -> None:
        """Dispose each child in reverse order, logging any failure."""
        for child in reversed(self._children):
            try:
                child.dispose()
            except Exception:
                self.context.logger.exception(
                    "Child service failed to dispose", child=child.name, parent=self.name
                )
