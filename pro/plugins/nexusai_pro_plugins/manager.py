"""The plugin manager — the public API.

Combines three collaborators: a ``PluginCatalog`` (the read side, built on the engine's
own discovery), a ``PluginInstaller`` (pip lifecycle) and an ``EnablementStore`` (the
enable/disable overlay). Every method maps to one of the required features:
install, update, enable, disable, remove, details, and version management.
"""

from __future__ import annotations

from .catalog import PluginCatalog
from .enablement import EnablementStore
from .installer import PluginInstaller
from .models import CatalogEntry, OperationResult, PluginView, RuntimeState


class PluginManager:
    def __init__(
        self,
        catalog: PluginCatalog,
        installer: PluginInstaller,
        enablement: EnablementStore,
    ) -> None:
        self._catalog = catalog
        self._installer = installer
        self._enablement = enablement

    # --- read side --------------------------------------------------------

    def list_plugins(self) -> list[PluginView]:
        """Every discovered plugin with its runtime state and enablement."""
        views = [self._view(entry) for entry in self._catalog.entries()]
        views.sort(key=lambda v: v.id)
        return views

    def details(self, plugin_id: str) -> PluginView | None:
        """Full detail for one plugin, or None if it is not present."""
        for entry in self._catalog.entries():
            if entry.id == plugin_id:
                return self._view(entry)
        return None

    def effective_plugin_names(self) -> list[str]:
        """Plugins that are both accepted by the engine and enabled in the Pro layer.

        Pro consumers (API, scheduler) honour this set when deciding which plugins to
        act on. Disabling never uninstalls; it just removes a plugin from this set.
        """
        return [
            v.id
            for v in self.list_plugins()
            if v.state is RuntimeState.LOADED and v.enabled
        ]

    # --- lifecycle --------------------------------------------------------

    def install(self, spec: str, *, version: str | None = None) -> OperationResult:
        return self._installer.install(spec, version=version)

    def update(self, distribution: str, *, version: str | None = None) -> OperationResult:
        return self._installer.update(distribution, version=version)

    def remove(self, plugin_id: str) -> OperationResult:
        """Uninstall the distribution that provides ``plugin_id`` and forget its state."""
        distribution = self._distribution_for(plugin_id) or plugin_id
        result = self._installer.remove(distribution)
        if result.ok:
            self._enablement.forget(plugin_id)
        return result

    # --- enablement -------------------------------------------------------

    def enable(self, plugin_id: str) -> OperationResult:
        self._enablement.set_enabled(plugin_id, True)
        return OperationResult(ok=True, action="enable", target=plugin_id, message=f"{plugin_id} enabled")

    def disable(self, plugin_id: str) -> OperationResult:
        self._enablement.set_enabled(plugin_id, False)
        return OperationResult(ok=True, action="disable", target=plugin_id, message=f"{plugin_id} disabled")

    # --- helpers ----------------------------------------------------------

    def _distribution_for(self, plugin_id: str) -> str | None:
        for entry in self._catalog.entries():
            if entry.id == plugin_id:
                return entry.distribution
        return None

    def _view(self, entry: CatalogEntry) -> PluginView:
        return PluginView(
            id=entry.id,
            enabled=self._enablement.is_enabled(entry.id),
            source=entry.source,
            state=entry.state,
            distribution=entry.distribution,
            distribution_version=entry.distribution_version,
            runtime=entry.runtime,
            reason=entry.reason,
        )
