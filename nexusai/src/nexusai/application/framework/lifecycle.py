"""Lifecycle management for a set of framework components.

Generalises the plugin lifecycle from Phase 2: initialise a collection in order,
then dispose it in reverse regardless of what happened in between. Disposal in
reverse order means a component that depends on an earlier one is torn down first,
while it can still rely on that dependency being present.

Two rules carry over. Initialisation failure is fatal -- a component that was
meant to start but could not means the run would silently do something different
-- and everything already initialised is disposed before the error propagates.
Disposal failure is logged and swallowed, because a component that cannot clean up
must not overwrite the outcome the operator actually needs to see.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field

from nexusai.domain.events.base import ComponentDisposed, ComponentInitialized
from nexusai.domain.model.context import FrameworkContext
from nexusai.domain.ports.events import EventPublisher
from nexusai.shared.lifecycle import Initializable, LifecycleAware


@dataclass(slots=True)
class LifecycleManager:
    """Initialises components in order and disposes them in reverse.

    Args:
        context: Ambient context, used for logging and event correlation.
        events: Optional publisher; when supplied, a component-lifecycle event is
            emitted as each component initialises and disposes, so that startup
            and shutdown are observable without the components themselves knowing.
    """

    context: FrameworkContext
    events: EventPublisher | None = None
    _initialised: list[LifecycleAware] = field(default_factory=list, init=False, repr=False)

    def initialize(self, components: Sequence[LifecycleAware]) -> None:
        """Initialise ``components`` in order.

        Raises:
            Exception: Whatever a component raises from ``initialize``. Everything
                already initialised is disposed before the error propagates, so a
                partial startup does not leak resources.
        """
        for component in components:
            try:
                component.initialize()
            except Exception:
                self.context.logger.exception(
                    "Component failed to initialise", component=_name_of(component)
                )
                self.dispose()
                raise
            self._initialised.append(component)
            self._announce(ComponentInitialized, _name_of(component))

    def dispose(self) -> None:
        """Dispose every initialised component in reverse order.

        A disposal failure is logged and does not prevent the remaining
        components from being disposed. Safe to call more than once.
        """
        while self._initialised:
            component = self._initialised.pop()
            try:
                component.dispose()
            except Exception:
                self.context.logger.exception(
                    "Component failed to dispose", component=_name_of(component)
                )
            else:
                self._announce(ComponentDisposed, _name_of(component))

    def _announce(self, event_type: type, component: str) -> None:
        if self.events is None:
            return
        self.events.publish(
            event_type(
                event_id=self.context.id_generator.new(),
                occurred_at=self.context.clock.now(),
                correlation_id=self.context.correlation_id,
                source="nexusai.application.framework.lifecycle",
                component=component,
            )
        )


@contextmanager
def managed_lifecycle(
    components: Sequence[LifecycleAware],
    context: FrameworkContext,
    *,
    events: EventPublisher | None = None,
) -> Iterator[LifecycleManager]:
    """Initialise ``components`` on entry and dispose them on exit.

    The disposal runs even when the body raises, so resources are released on the
    failure path as reliably as on the success path.
    """
    manager = LifecycleManager(context=context, events=events)
    manager.initialize(components)
    try:
        yield manager
    finally:
        manager.dispose()


def _name_of(component: object) -> str:
    """Best-effort human name for a component, for logs and events."""
    name = getattr(component, "name", None)
    if isinstance(name, str) and name:
        return name
    return type(component).__name__


# Re-exported so callers can annotate against the initialisation contract without
# reaching into the shared package directly.
__all__ = ["Initializable", "LifecycleManager", "managed_lifecycle"]
