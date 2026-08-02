"""Controlled plugin resolution.

Configuration names the implementations a run should use -- an adapter, an
exporter, a validator -- and this resolver turns those names into plugins through
the approved registry, refusing anything the registry does not vouch for. It is
the barrier against configuration naming an arbitrary module: resolution is a
lookup in a registry of already-vetted plugins, never a dynamic import of a path
from config, so untrusted configuration cannot cause untrusted code to load.

An unknown name, or a name at the wrong extension point, is an explicit error --
the run refuses to start rather than silently skipping a component the operator
asked for.
"""

from __future__ import annotations

from nexusai.domain.errors.exceptions import PluginError
from nexusai.domain.model.plugin import ExtensionPoint
from nexusai.domain.ports.plugins import Plugin, PluginRegistry


class PluginResolver:
    """Resolves configured plugin names through the vetted registry."""

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def resolve(self, extension_point: ExtensionPoint, name: str) -> Plugin:
        """Return the registered plugin, or raise if it is not present.

        Raises:
            PluginError: If no plugin with ``name`` is registered at
                ``extension_point``.
        """
        if not self._registry.has(extension_point, name):
            raise PluginError(
                "Configured plugin is not registered",
                extension_point=extension_point.value,
                name=name,
            )
        return self._registry.get(extension_point, name)

    def resolve_all(self, extension_point: ExtensionPoint, names: list[str]) -> list[Plugin]:
        """Resolve several plugin names at one extension point."""
        return [self.resolve(extension_point, name) for name in names]
