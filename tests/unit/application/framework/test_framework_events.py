"""Tests for the typed subscriber and subscribe helper."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nexusai.application.framework.events import TypedSubscriber, subscribe
from nexusai.domain.events.base import (
    ComponentInitialized,
    DomainEvent,
    FrameworkStarted,
)


def _initialized(component: str) -> ComponentInitialized:
    return ComponentInitialized(
        event_id="e1",
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        source="test",
        component=component,
    )


def _started() -> FrameworkStarted:
    return FrameworkStarted(
        event_id="e2",
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        source="test",
        version="0.1.0",
    )


class CollectInitialized(TypedSubscriber[ComponentInitialized]):
    event_type = ComponentInitialized

    def __init__(self) -> None:
        super().__init__()
        self.seen: list[str] = []

    def on_event(self, event: ComponentInitialized) -> None:
        self.seen.append(event.component)


def test_typed_subscriber_declares_its_event_type() -> None:
    subscriber = CollectInitialized()
    assert subscriber.handled_events == (ComponentInitialized,)
    assert subscriber.label == "CollectInitialized"


def test_typed_subscriber_dispatches_matching_event() -> None:
    subscriber = CollectInitialized()
    subscriber.handle(_initialized("exporter"))
    assert subscriber.seen == ["exporter"]


def test_typed_subscriber_ignores_non_matching_event() -> None:
    subscriber = CollectInitialized()
    subscriber.handle(_started())
    assert subscriber.seen == []


def test_typed_subscriber_without_event_type_is_rejected() -> None:
    class Broken(TypedSubscriber[DomainEvent]):
        pass  # no event_type set

    with pytest.raises(TypeError, match="must set a class-level 'event_type'"):
        Broken()


def test_default_on_event_raises_not_implemented() -> None:
    class Bare(TypedSubscriber[FrameworkStarted]):
        event_type = FrameworkStarted

    with pytest.raises(NotImplementedError):
        Bare().handle(_started())


def test_custom_label_is_used() -> None:
    class Labelled(TypedSubscriber[FrameworkStarted]):
        event_type = FrameworkStarted

        def on_event(self, event: FrameworkStarted) -> None:  # pragma: no cover - trivial
            pass

    assert Labelled("custom").label == "custom"


class _RecordingBus:
    """A minimal bus double capturing subscribe calls."""

    def __init__(self) -> None:
        self.subscribed: list[object] = []

    def subscribe(self, subscriber: object) -> None:
        self.subscribed.append(subscriber)


def test_subscribe_registers_all_subscribers() -> None:
    bus = _RecordingBus()
    subscribers = [CollectInitialized(), CollectInitialized()]
    subscribe(bus, subscribers)
    assert bus.subscribed == subscribers


def test_subscribe_rejects_publisher_without_subscribe() -> None:
    with pytest.raises(TypeError, match="subscribe"):
        subscribe(object(), [])
