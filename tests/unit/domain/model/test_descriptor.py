"""Tests for PluginDescriptor."""

from __future__ import annotations

from nexusai.domain.model.descriptor import PluginDescriptor, PluginState
from nexusai.domain.model.plugin import (
    ApiVersion,
    ExtensionPoint,
    PluginMetadata,
)
from nexusai.shared.lifecycle import LifecycleState


def _metadata() -> PluginMetadata:
    return PluginMetadata(
        name="csv",
        version="1.0.0",
        extension_point=ExtensionPoint.EXPORTER,
        api_version=ApiVersion(1, 0),
        description="CSV exporter",
        author="tester",
    )


def _descriptor(state: PluginState = PluginState.DISCOVERED) -> PluginDescriptor:
    return PluginDescriptor(metadata=_metadata(), origin="entry-point:csv", state=state)


def test_qualified_name_delegates_to_metadata() -> None:
    assert _descriptor().qualified_name == "exporter:csv"


def test_is_active_only_for_registered_or_initialised() -> None:
    assert _descriptor(PluginState.REGISTERED).is_active
    assert _descriptor(PluginState.INITIALISED).is_active
    assert not _descriptor(PluginState.DISCOVERED).is_active
    assert not _descriptor(PluginState.DISPOSED).is_active
    assert not _descriptor(PluginState.REJECTED).is_active


def test_in_state_returns_advanced_copy() -> None:
    original = _descriptor()
    rejected = original.in_state(PluginState.REJECTED, detail="bad api")
    assert original.state is PluginState.DISCOVERED
    assert rejected.state is PluginState.REJECTED
    assert rejected.detail == "bad api"


def test_in_state_preserves_existing_detail_when_blank() -> None:
    original = _descriptor().in_state(PluginState.REGISTERED, detail="note")
    advanced = original.in_state(PluginState.INITIALISED)
    assert advanced.detail == "note"


def test_from_lifecycle_maps_states() -> None:
    assert PluginDescriptor.from_lifecycle(LifecycleState.CREATED) is PluginState.REGISTERED
    assert PluginDescriptor.from_lifecycle(LifecycleState.INITIALISED) is PluginState.INITIALISED
    assert PluginDescriptor.from_lifecycle(LifecycleState.DISPOSED) is PluginState.DISPOSED


def test_serialisation_includes_metadata_and_state() -> None:
    payload = _descriptor(PluginState.REGISTERED).to_dict()
    assert payload["state"] == "registered"
    assert payload["origin"] == "entry-point:csv"
    assert payload["metadata"]["extension_point"] == "exporter"
    assert payload["metadata"]["api_version"] == "1.0"
