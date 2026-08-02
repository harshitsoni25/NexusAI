"""The plugin registry."""

from __future__ import annotations

import pytest

from nexusai.domain.errors import PluginError
from nexusai.domain.model.plugin import ExtensionPoint
from nexusai.infrastructure.plugins.registry import InMemoryPluginRegistry
from nexusai.testing import StubPlugin


def test_a_registered_plugin_can_be_retrieved() -> None:
    registry = InMemoryPluginRegistry()
    plugin = StubPlugin(name="csv")
    registry.register(plugin)
    assert registry.get(ExtensionPoint.EXPORTER, "csv") is plugin
    assert registry.has(ExtensionPoint.EXPORTER, "csv")


def test_the_same_name_under_different_extension_points_does_not_collide() -> None:
    registry = InMemoryPluginRegistry()
    registry.register(StubPlugin(name="csv", extension_point=ExtensionPoint.EXPORTER))
    registry.register(StubPlugin(name="csv", extension_point=ExtensionPoint.STORAGE_PROVIDER))
    assert len(registry) == 2


def test_duplicate_registration_is_rejected() -> None:
    registry = InMemoryPluginRegistry()
    registry.register(StubPlugin(name="csv", version="1.0.0"))
    with pytest.raises(PluginError, match="already registered") as caught:
        registry.register(StubPlugin(name="csv", version="2.0.0"))
    # Both versions are named, because the usual cause is two installed
    # distributions competing for the same slot.
    assert caught.value.context["existing_version"] == "1.0.0"
    assert caught.value.context["incoming_version"] == "2.0.0"


def test_an_unknown_name_lists_what_is_available() -> None:
    # A typo in a configured plugin name is the overwhelmingly common cause.
    registry = InMemoryPluginRegistry()
    registry.register(StubPlugin(name="parquet"))
    with pytest.raises(PluginError, match="No plugin is registered") as caught:
        registry.get(ExtensionPoint.EXPORTER, "parquett")
    assert caught.value.context["available"] == ("parquet",)


def test_freezing_prevents_further_registration() -> None:
    registry = InMemoryPluginRegistry()
    registry.freeze()
    with pytest.raises(PluginError, match="frozen"):
        registry.register(StubPlugin())


def test_freezing_is_idempotent() -> None:
    registry = InMemoryPluginRegistry()
    registry.freeze()
    registry.freeze()
    assert registry.frozen is True


def test_all_for_filters_by_extension_point() -> None:
    registry = InMemoryPluginRegistry()
    registry.register(StubPlugin(name="csv", extension_point=ExtensionPoint.EXPORTER))
    registry.register(StubPlugin(name="sqlite", extension_point=ExtensionPoint.STORAGE_PROVIDER))
    assert len(registry.all_for(ExtensionPoint.EXPORTER)) == 1
    assert registry.all_for(ExtensionPoint.MIDDLEWARE) == []


def test_missing_plugins_report_absence_rather_than_raising() -> None:
    assert InMemoryPluginRegistry().has(ExtensionPoint.EXPORTER, "nope") is False


def test_describe_is_ordered_for_stable_display() -> None:
    registry = InMemoryPluginRegistry()
    registry.register(StubPlugin(name="zeta"))
    registry.register(StubPlugin(name="alpha"))
    assert [item.name for item in registry.describe()] == ["alpha", "zeta"]


def test_the_registry_is_iterable() -> None:
    registry = InMemoryPluginRegistry()
    registry.register(StubPlugin(name="a"))
    assert len(list(registry)) == 1
