"""Plugin initialisation and disposal."""

from __future__ import annotations

import pytest

from nexusai.domain.errors import PluginError
from nexusai.infrastructure.plugins.lifecycle import plugin_lifecycle
from nexusai.infrastructure.plugins.registry import InMemoryPluginRegistry
from nexusai.testing import RecordingLogger, StubPlugin


def registry_with(*plugins: StubPlugin) -> InMemoryPluginRegistry:
    registry = InMemoryPluginRegistry()
    for plugin in plugins:
        registry.register(plugin)
    return registry


def test_every_plugin_is_initialised_and_disposed(logger: RecordingLogger) -> None:
    plugin = StubPlugin(name="a")
    with plugin_lifecycle(registry_with(plugin), logger):
        assert plugin.initialised is True
        assert plugin.disposed is False
    assert plugin.disposed is True


def test_disposal_happens_even_when_the_run_fails(logger: RecordingLogger) -> None:
    plugin = StubPlugin(name="a")
    with (
        pytest.raises(RuntimeError, match="run failed"),
        plugin_lifecycle(registry_with(plugin), logger),
    ):
        raise RuntimeError("run failed")
    assert plugin.disposed is True


def test_initialisation_failure_is_fatal(logger: RecordingLogger) -> None:
    # A plugin already accepted into the registry is one the run intends to use.
    # Continuing without it would silently change what the run does.
    plugin = StubPlugin(name="bad", fail_on_initialize=True)
    with (
        pytest.raises(PluginError, match="failed to initialise"),
        plugin_lifecycle(registry_with(plugin), logger),
    ):
        pass  # pragma: no cover - the context manager raises on entry


def test_plugins_already_initialised_are_disposed_when_a_later_one_fails(
    logger: RecordingLogger,
) -> None:
    good = StubPlugin(name="a")
    bad = StubPlugin(name="b", fail_on_initialize=True)
    with pytest.raises(PluginError), plugin_lifecycle(registry_with(good, bad), logger):
        pass  # pragma: no cover
    assert good.disposed is True


def test_a_disposal_failure_is_logged_and_swallowed(logger: RecordingLogger) -> None:
    # A plugin that cannot clean up must not overwrite the outcome of the run,
    # which is the information the operator actually needs.
    plugin = StubPlugin(name="a", fail_on_dispose=True)
    with plugin_lifecycle(registry_with(plugin), logger):
        pass
    assert logger.has_message("Plugin failed to dispose cleanly", level="WARNING")


def test_disposal_runs_in_reverse_order_of_initialisation(logger: RecordingLogger) -> None:
    order: list[str] = []

    class Ordered(StubPlugin):
        def dispose(self) -> None:
            order.append(self.name)

    with plugin_lifecycle(registry_with(Ordered(name="a"), Ordered(name="b")), logger):
        pass
    assert order == ["b", "a"]


def test_an_empty_registry_is_fine(logger: RecordingLogger) -> None:
    with plugin_lifecycle(InMemoryPluginRegistry(), logger) as registry:
        assert len(registry) == 0
