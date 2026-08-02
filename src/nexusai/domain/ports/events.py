"""Ports for event publication and subscription.

The event bus carries *observational* events only. Control flow never depends on
a subscriber (ADR-0009): a subscriber may log, measure, render progress or send
a notification, but the pipeline behaves identically whether or not it is
present. This restriction keeps execution order explicit and debuggable.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from nexusai.domain.events.base import DomainEvent


@runtime_checkable
class EventPublisher(Protocol):
    """Publishes events to interested subscribers."""

    def publish(self, event: DomainEvent) -> None:
        """Deliver ``event`` to every subscriber that handles its type.

        Must never raise as a result of subscriber failure. A failing subscriber
        is an observability problem; it must not become an execution problem.
        """
        ...


@runtime_checkable
class EventSubscriber(Protocol):
    """Receives events it has declared an interest in."""

    @property
    def handled_events(self) -> Sequence[type[DomainEvent]]:
        """Event types this subscriber wants, subclasses included."""
        ...

    def handle(self, event: DomainEvent) -> None:
        """Process ``event``."""
        ...
