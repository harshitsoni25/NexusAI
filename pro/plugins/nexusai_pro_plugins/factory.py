"""Convenience wiring for a ready-to-use manager backed by the real engine."""

from __future__ import annotations

from pathlib import Path

from .catalog import BootstrapReportProvider, EntryPointCatalog
from .config import PluginManagerConfig
from .enablement import EnablementStore
from .installer import PluginInstaller
from .manager import PluginManager


def build_manager(config: PluginManagerConfig | None = None, *, config_file: Path | None = None) -> PluginManager:
    """Build a PluginManager that reuses the engine's discovery and pip lifecycle."""
    config = config or PluginManagerConfig()
    catalog = EntryPointCatalog(
        BootstrapReportProvider(config_file=config_file),
        group=config.entry_point_group,
    )
    enablement = EnablementStore(config.enablement_path)
    return PluginManager(catalog, PluginInstaller(), enablement)
