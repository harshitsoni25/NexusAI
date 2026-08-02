"""Event dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from nexusai.domain.events.base import DomainEvent, FrameworkStarted
from nexusai.infrastructure.events.bus import InProcessEventBus, callback_subscriber
from nexusai.testing import FrozenClock, RecordingLogger, RecordingSubscriber

WHEN = datetime(2026, 3, 1, tzinfo=UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class OtherEvent(DomainEvent):
    """An unrelated event type, for checking that filtering works."""


def make_bus(logger: RecordingLogger, clock: FrozenClock) -> InProcessEventBus:
    return InProcessEventBus(logger=logger, clock=clock)


def event() -> FrameworkStarted:
    return FrameworkStarted(event_id="e-1", occurred_at=WHEN, version="1.0.0")


def test_subscribers_receive_matching_events(logger: RecordingLogger, clock: FrozenClock) -> None:
    bus = make_bus(logger, clock)
    subscriber = RecordingSubscriber(event_types=(FrameworkStarted,))
    bus.subscribe(subscriber)
    bus.publish(event())
    assert len(subscriber.received) == 1


def test_subscribers_do_not_receive_unrelated_events(
    logger: RecordingLogger, clock: FrozenClock
) -> None:
    bus = make_bus(logger, clock)
    subscriber = RecordingSubscriber(event_types=(OtherEvent,))
    bus.subscribe(subscriber)
    bus.publish(event())
    assert subscriber.received == []


def test_a_base_type_subscription_receives_subclasses(
    logger: RecordingLogger, clock: FrozenClock
) -> None:
    bus = make_bus(logger, clock)
    subscriber = RecordingSubscriber(event_types=(DomainEvent,))
    bus.subscribe(subscriber)
    bus.publish(event())
    assert len(subscriber.received) == 1


def test_publishing_with_no_subscribers_is_harmless(
    logger: RecordingLogger, clock: FrozenClock
) -> None:
    make_bus(logger, clock).publish(event())


def test_a_failing_subscriber_does_not_stop_delivery_to_the_others(
    logger: RecordingLogger, clock: FrozenClock
) -> None:
    # An observability problem must never become an execution problem.
    bus = make_bus(logger, clock)
    failing = RecordingSubscriber(fail_with=RuntimeError("boom"), label="failing")
    healthy = RecordingSubscriber(label="healthy")
    bus.subscribe(failing)
    bus.subscribe(healthy)
    bus.publish(event())
    assert len(healthy.received) == 1
    assert logger.has_message("Event subscriber failed", level="ERROR")


def test_a_failing_subscriber_is_identified_in_the_log(
    logger: RecordingLogger, clock: FrozenClock
) -> None:
    bus = make_bus(logger, clock)
    bus.subscribe(RecordingSubscriber(fail_with=RuntimeError("boom"), label="the-bad-one"))
    bus.publish(event())
    assert logger.records[0].fields["subscriber"] == "the-bad-one"


def test_a_slow_subscriber_is_reported(logger: RecordingLogger, clock: FrozenClock) -> None:
    # A silently slow subscriber looks exactly like a slow pipeline.
    bus = InProcessEventBus(logger=logger, clock=clock, slow_subscriber_threshold_seconds=0.1)
    bus.subscribe(RecordingSubscriber(delay_seconds=0.5, clock=clock, label="sluggish"))
    bus.publish(event())
    assert logger.has_message("Event subscriber is slow", level="WARNING")


def test_a_fast_subscriber_is_not_reported(logger: RecordingLogger, clock: FrozenClock) -> None:
    bus = InProcessEventBus(logger=logger, clock=clock, slow_subscriber_threshold_seconds=1.0)
    bus.subscribe(RecordingSubscriber(delay_seconds=0.01, clock=clock))
    bus.publish(event())
    assert not logger.has_message("Event subscriber is slow")


def test_unsubscribing_stops_delivery(logger: RecordingLogger, clock: FrozenClock) -> None:
    bus = make_bus(logger, clock)
    subscriber = RecordingSubscriber()
    bus.subscribe(subscriber)
    bus.unsubscribe(subscriber)
    bus.publish(event())
    assert subscriber.received == []
    assert bus.subscriber_count == 0


def test_unsubscribing_an_unknown_subscriber_is_a_no_op(
    logger: RecordingLogger, clock: FrozenClock
) -> None:
    make_bus(logger, clock).unsubscribe(RecordingSubscriber())


def test_a_subscriber_with_no_declared_types_is_rejected(
    logger: RecordingLogger, clock: FrozenClock
) -> None:
    # Registering it would silently do nothing, which is worse than failing.
    bus = make_bus(logger, clock)
    try:
        bus.subscribe(RecordingSubscriber(event_types=()))
    except ValueError as error:
        assert "never be called" in str(error)
    else:  # pragma: no cover - the assertion above is the contract
        raise AssertionError("expected ValueError")


def test_a_callable_can_subscribe(logger: RecordingLogger, clock: FrozenClock) -> None:
    seen: list[DomainEvent] = []
    bus = make_bus(logger, clock)
    bus.subscribe(callback_subscriber(FrameworkStarted, callback=seen.append, label="collector"))
    bus.publish(event())
    assert len(seen) == 1


def test_a_callable_subscriber_must_declare_a_type() -> None:
    try:
        callback_subscriber(callback=lambda _: None)
    except ValueError as error:
        assert "at least one event type" in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_subscriber_count_reflects_registrations(
    logger: RecordingLogger, clock: FrozenClock
) -> None:
    bus = make_bus(logger, clock)
    bus.subscribe(RecordingSubscriber())
    bus.subscribe(RecordingSubscriber())
    assert bus.subscriber_count == 2
