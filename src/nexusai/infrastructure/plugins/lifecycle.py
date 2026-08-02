"""Plugin initialisation and disposal.

Lifecycle is scoped to a run and expressed as a context manager, so disposal
happens even when the run fails. Disposal failures are logged and swallowed: a
plugin that cannot clean up must not overwrite the outcome of the run itself,
which is the information the operator actually needs.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from nexusai.domain.errors import PluginError
from nexusai.domain.ports.observability import Logger
from nexusai.domain.ports.plugins import Plugin
from nexusai.infrastructure.plugins.registry import InMemoryPluginRegistry


@contextmanager
def plugin_lifecycle(
    registry: InMemoryPluginRegistry, logger: Logger
) -> Iterator[InMemoryPluginRegistry]:
    """Initialise every registered plugin, then dispose of them all on exit.

    Initialisation failure is fatal, unlike discovery failure: a plugin that has
    been accepted into the registry is one the run intends to use, so starting
    without it would silently change what the run does.

    Raises:
        PluginError: If a plugin fails to initialise. Plugins already
            initialised are disposed of before the error propagates.
    """
    initialised: list[Plugin] = []
    try:
        for plugin in registry:
            try:
                plugin.initialize()
            except Exception as exc:
                raise PluginError(
                    "Plugin failed to initialise",
                    plugin=plugin.metadata.qualified_name,
                    error=str(exc),
                ) from exc
            initialised.append(plugin)
            logger.debug("Plugin initialised", plugin=plugin.metadata.qualified_name)
        yield registry
    finally:
        for plugin in reversed(initialised):
            try:
                plugin.dispose()
            except Exception as exc:  # noqa: BLE001 - disposal must never mask the outcome
                logger.warning(
                    "Plugin failed to dispose cleanly",
                    plugin=plugin.metadata.qualified_name,
                    error=str(exc),
                )
