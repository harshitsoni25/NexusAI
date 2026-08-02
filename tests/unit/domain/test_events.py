"""The domain event base."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nexusai.domain.events.base import DomainEvent, FrameworkStarted
from nexusai.shared.identifiers import CorrelationId

WHEN = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


def test_event_name_is_the_type_name() -> None:
    event = DomainEvent(event_id="e1", occurred_at=WHEN)
    assert event.name == "DomainEvent"


def test_events_are_immutable() -> None:
    event = DomainEvent(event_id="e1", occurred_at=WHEN)
    with pytest.raises(AttributeError):
        event.event_id = "e2"  # type: ignore[misc]


def test_serialisation_includes_the_correlation_id_when_present() -> None:
    event = DomainEvent(event_id="e1", occurred_at=WHEN, correlation_id=CorrelationId("c-1"))
    assert event.to_dict()["correlation_id"] == "c-1"


def test_serialisation_tolerates_an_absent_correlation_id() -> None:
    assert DomainEvent(event_id="e1", occurred_at=WHEN).to_dict()["correlation_id"] is None


def test_subclasses_extend_the_payload() -> None:
    event = FrameworkStarted(event_id="e1", occurred_at=WHEN, version="9.9.9")
    payload = event.to_dict()
    assert payload["event"] == "FrameworkStarted"
    assert payload["version"] == "9.9.9"
    assert payload["occurred_at"] == WHEN.isoformat()
