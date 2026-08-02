"""Reusable helpers for wiring subscribers onto the Phase 2 event bus.

The bus and its ``EventSubscriber`` contract exist already. What later phases
repeat is the boilerplate around them: declaring which event types a subscriber
handles, and wiring a handful of subscribers onto a publisher at startup. These
helpers remove that repetition without adding a new dispatch mechanism -- the bus
remains the one and only carrier.

``TypedSubscriber`` also narrows the event to its declared type before handing it
to the handler, so a subscriber body works with a precise type rather than the
``DomainEvent`` base and a manual ``isinstance`` check.
"""

from __future__ import annotations

from collections.abc import Sequence

from nexusai.domain.events.base import DomainEvent
from nexusai.domain.ports.events import EventSubscriber


class TypedSubscriber[E: DomainEvent]:
    """A subscriber for a single event type, with the narrowing handled.

    Subclasses set :attr:`event_type` and implement :meth:`on_event`, which
    receives the event already narrowed to that type. The base satisfies the
    ``EventSubscriber`` protocol, so an instance can be handed straight to the
    bus.
    """

    event_type: type[E]

    def __init__(self, label: str | None = None) -> None:
        if not hasattr(self, "event_type"):
            raise TypeError(f"{type(self).__name__} must set a class-level 'event_type'")
        self._label = label or type(self).__name__

    @property
    def label(self) -> str:
        """Name used in the bus's failure and slow-subscriber reporting."""
        return self._label

    @property
    def handled_events(self) -> Sequence[type[DomainEvent]]:
        """The single event type this subscriber handles."""
        return (self.event_type,)

    def handle(self, event: DomainEvent) -> None:
        """Narrow ``event`` to the declared type and dispatch it."""
        if isinstance(event, self.event_type):
            self.on_event(event)

    def on_event(self, event: E) -> None:
        """Handle an event of the declared type. Implemented by subclasses."""
        raise NotImplementedError


def subscribe(publisher: object, subscribers: Sequence[EventSubscriber]) -> None:
    """Register several subscribers on a bus that exposes ``subscribe``.

    A small convenience for the startup path, where a fixed set of observers is
    attached in one place. Typed against the structural presence of a
    ``subscribe`` method so it works with the in-process bus without this layer
    importing the infrastructure implementation.

    Raises:
        TypeError: If ``publisher`` has no ``subscribe`` method.
    """
    register = getattr(publisher, "subscribe", None)
    if not callable(register):
        raise TypeError("publisher does not expose a subscribe() method")
    for subscriber in subscribers:
        register(subscriber)
