"""Tests for the framework-lifecycle domain events."""

from __future__ import annotations

from datetime import UTC, datetime

from nexusai.domain.events.base import ComponentDisposed, ComponentInitialized
from nexusai.shared.identifiers import CorrelationId


def _fields() -> dict[str, object]:
    return {
        "event_id": "e1",
        "occurred_at": datetime(2026, 1, 1, tzinfo=UTC),
        "correlation_id": CorrelationId("c1"),
        "source": "test",
        "component": "exporter",
    }


def test_component_initialized_serialises_with_component() -> None:
    payload = ComponentInitialized(**_fields()).to_dict()  # type: ignore[arg-type]
    assert payload["component"] == "exporter"
    assert payload["event_id"] == "e1"
    assert payload["correlation_id"] == "c1"


def test_component_disposed_serialises_with_component() -> None:
    payload = ComponentDisposed(**_fields()).to_dict()  # type: ignore[arg-type]
    assert payload["component"] == "exporter"
    assert payload["source"] == "test"
