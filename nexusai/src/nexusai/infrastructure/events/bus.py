"""In-process, synchronous event bus.

Dispatch is synchronous and in-order because the bus carries observational
events only (ADR-0009). Asynchronous dispatch would buy isolation from slow
subscribers at the cost of making the relationship between an occurrence and its
log line non-deterministic -- a poor trade for a framework whose main job is to
explain what happened.

Two properties are non-negotiable. A subscriber that raises must not fail the
publisher: an observability problem must never become an execution problem. And
a subscriber that is slow must be *visible*, because a silently slow subscriber
looks exactly like a slow pipeline.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from nexusai.domain.events.base import DomainEvent
from nexusai.domain.ports.events import EventSubscriber
from nexusai.domain.ports.observability import Clock, Logger


@dataclass(frozen=True, slots=True)
class _CallbackSubscriber:
    """Adapts a plain callable to the ``EventSubscriber`` protocol."""

    event_types: tuple[type[DomainEvent], ...]
    callback: Callable[[DomainEvent], None]
    label: str

    @property
    def handled_events(self) -> Sequence[type[DomainEvent]]:
        return self.event_types

    def handle(self, event: DomainEvent) -> None:
        self.callback(event)


def callback_subscriber(
    *event_types: type[DomainEvent],
    callback: Callable[[DomainEvent], None],
    label: str = "callback",
) -> EventSubscriber:
    """Wrap ``callback`` so it can be subscribed to the bus.

    Args:
        event_types: Event types to receive; subclasses are included.
        callback: Invoked for each matching event.
        label: Name used in log output when the callback fails or runs slowly.
    """
    if not event_types:
        raise ValueError("A subscriber must declare at least one event type")
    return _CallbackSubscriber(tuple(event_types), callback, label)


@dataclass(slots=True)
class InProcessEventBus:
    """Delivers events to subscribers within the current process.

    Args:
        logger: Used to report subscriber failures and slow subscribers.
        clock: Source of monotonic time for measuring subscriber duration.
        slow_subscriber_threshold_seconds: Duration above which a subscriber is
            reported as slow.
    """

    logger: Logger
    clock: Clock
    slow_subscriber_threshold_seconds: float = 0.5
    _subscribers: list[EventSubscriber] = field(default_factory=list, init=False, repr=False)

    def subscribe(self, subscriber: EventSubscriber) -> None:
        """Register ``subscriber`` for the event types it declares."""
        if not subscriber.handled_events:
            raise ValueError(
                f"{_describe(subscriber)} declares no handled events and would never be called"
            )
        self._subscribers.append(subscriber)

    def unsubscribe(self, subscriber: EventSubscriber) -> None:
        """Remove ``subscriber``. Removing an unknown subscriber is a no-op."""
        if subscriber in self._subscribers:
            self._subscribers.remove(subscriber)

    @property
    def subscriber_count(self) -> int:
        """How many subscribers are currently registered."""
        return len(self._subscribers)

    def publish(self, event: DomainEvent) -> None:
        """Deliver ``event`` to every subscriber that handles its type.

        Never raises as a result of subscriber behaviour. Delivery continues
        after a failing subscriber, so one broken listener cannot silence the
        others.
        """
        for subscriber in tuple(self._subscribers):
            if not _handles(subscriber, event):
                continue
            started = self.clock.monotonic()
            try:
                subscriber.handle(event)
            except Exception:
                self.logger.exception(
                    "Event subscriber failed",
                    subscriber=_describe(subscriber),
                    event=event.name,
                    event_id=event.event_id,
                )
                continue
            elapsed = self.clock.monotonic() - started
            if elapsed >= self.slow_subscriber_threshold_seconds:
                self.logger.warning(
                    "Event subscriber is slow",
                    subscriber=_describe(subscriber),
                    event=event.name,
                    seconds=round(elapsed, 4),
                    threshold_seconds=self.slow_subscriber_threshold_seconds,
                )


def _handles(subscriber: EventSubscriber, event: DomainEvent) -> bool:
    return isinstance(event, tuple(subscriber.handled_events))


def _describe(subscriber: EventSubscriber) -> str:
    label = getattr(subscriber, "label", None)
    return str(label) if label else type(subscriber).__name__
