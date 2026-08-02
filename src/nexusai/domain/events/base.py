"""The base type for all domain events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from nexusai.shared.identifiers import CorrelationId


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """An immutable statement that something happened.

    Events are constructed by whichever component observed the occurrence, which
    is also the component holding a clock and an identifier generator. The
    domain therefore never reaches for the current time itself, and event
    timestamps stay deterministic under test.

    Attributes:
        event_id: Unique identifier for this occurrence.
        occurred_at: When the event happened, in UTC.
        correlation_id: Ties the event to the execution that produced it.
        source: Dotted name of the component that emitted the event.
    """

    event_id: str
    occurred_at: datetime
    correlation_id: CorrelationId | None = None
    source: str = "nexusai"

    @property
    def name(self) -> str:
        """The event type name, used for logging and metric tags."""
        return type(self).__name__

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation for logs and reports."""
        return {
            "event": self.name,
            "event_id": self.event_id,
            "occurred_at": self.occurred_at.isoformat(),
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class FrameworkStarted(DomainEvent):
    """Emitted once when the composition root has finished wiring the system.

    This is framework lifecycle rather than business activity, so it belongs
    here rather than with the business events of later phases. It gives the
    logging and metrics subscribers something real to observe from the very
    first phase, which is what makes the event infrastructure verifiable now
    rather than in theory.
    """

    version: str

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation including the framework version."""
        # Explicit rather than ``super()``: ``slots=True`` rebuilds the class,
        # which invalidates the zero-argument super() closure cell.
        payload = DomainEvent.to_dict(self)
        payload["version"] = self.version
        return payload


@dataclass(frozen=True, slots=True, kw_only=True)
class ComponentInitialized(DomainEvent):
    """Emitted when a framework component completes initialisation.

    A framework-lifecycle event, not a business event: it reports that a piece of
    the framework came up, which is exactly the kind of observational signal the
    event bus exists to carry. It gives logging and metrics something concrete to
    observe as components start, without any component depending on a subscriber.
    """

    component: str

    def to_dict(self) -> dict[str, Any]:
        """Return the base payload extended with the component name."""
        payload = DomainEvent.to_dict(self)
        payload["component"] = self.component
        return payload


@dataclass(frozen=True, slots=True, kw_only=True)
class ComponentDisposed(DomainEvent):
    """Emitted when a framework component completes disposal."""

    component: str

    def to_dict(self) -> dict[str, Any]:
        """Return the base payload extended with the component name."""
        payload = DomainEvent.to_dict(self)
        payload["component"] = self.component
        return payload
