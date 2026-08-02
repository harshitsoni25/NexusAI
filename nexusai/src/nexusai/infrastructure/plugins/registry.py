"""The per-run plugin registry.

The registry is built once during composition and frozen before execution
begins. Freezing matters: a registry that can change mid-run would mean two
records in the same dataset could be produced by different implementations of
the same extension point, which would make a run impossible to reason about
afterwards.

The registry is passed explicitly to whatever needs it. It is not a service
locator (section 13): consumers receive the specific plugins they need through
their constructors, resolved at the composition root.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field

from nexusai.domain.errors import PluginError
from nexusai.domain.model.plugin import ExtensionPoint, PluginMetadata
from nexusai.domain.ports.plugins import Plugin


@dataclass(slots=True)
class InMemoryPluginRegistry:
    """Holds every plugin registered for the current run."""

    _plugins: dict[tuple[ExtensionPoint, str], Plugin] = field(default_factory=dict, repr=False)
    _frozen: bool = field(default=False, repr=False)

    def register(self, plugin: Plugin) -> None:
        """Add ``plugin`` to the registry.

        Raises:
            PluginError: If the registry is frozen, or a plugin is already
                registered under the same extension point and name.
        """
        metadata = plugin.metadata
        if self._frozen:
            raise PluginError(
                "Cannot register a plugin after the registry has been frozen",
                plugin=metadata.qualified_name,
            )
        key = (metadata.extension_point, metadata.name)
        if key in self._plugins:
            existing = self._plugins[key].metadata
            raise PluginError(
                "A plugin is already registered under this name",
                plugin=metadata.qualified_name,
                existing_version=existing.version,
                incoming_version=metadata.version,
            )
        self._plugins[key] = plugin

    def freeze(self) -> None:
        """Prevent further registration. Idempotent."""
        self._frozen = True

    @property
    def frozen(self) -> bool:
        """Whether the registry is closed to further registration."""
        return self._frozen

    def get(self, extension_point: ExtensionPoint, name: str) -> Plugin:
        """Return the named plugin.

        Raises:
            PluginError: If no plugin is registered under that name. The message
                lists what *is* registered, because a typo in a configured
                plugin name is the overwhelmingly common cause.
        """
        try:
            return self._plugins[(extension_point, name)]
        except KeyError:
            available = sorted(plugin.metadata.name for plugin in self.all_for(extension_point))
            raise PluginError(
                "No plugin is registered under this name",
                extension_point=extension_point.value,
                name=name,
                available=tuple(available),
            ) from None

    def all_for(self, extension_point: ExtensionPoint) -> Sequence[Plugin]:
        """Return every plugin registered for ``extension_point``."""
        return [plugin for (point, _), plugin in self._plugins.items() if point is extension_point]

    def has(self, extension_point: ExtensionPoint, name: str) -> bool:
        """Whether a plugin is registered under that name."""
        return (extension_point, name) in self._plugins

    def __len__(self) -> int:
        return len(self._plugins)

    def __iter__(self) -> Iterator[Plugin]:
        return iter(self._plugins.values())

    def describe(self) -> Sequence[PluginMetadata]:
        """Return the metadata of every registered plugin, ordered for display."""
        return sorted(
            (plugin.metadata for plugin in self._plugins.values()),
            key=lambda item: item.qualified_name,
        )
