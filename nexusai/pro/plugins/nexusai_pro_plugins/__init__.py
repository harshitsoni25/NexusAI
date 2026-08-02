"""Nexus AI Pro plugin manager.

A management overlay over the engine's existing plugin system (entry-point discovery,
LoadReport, plugin protocol). It adds install/update/remove (pip), enable/disable
(persisted overlay), details and version management — without redesigning or modifying
the engine's plugin implementation."""

from .catalog import (
    BootstrapReportProvider,
    EntryPointCatalog,
    PluginCatalog,
    ReportProvider,
)
from .config import PluginManagerConfig
from .enablement import EnablementStore
from .factory import build_manager
from .installer import CommandRunner, PipRunner, PluginInstaller
from .manager import PluginManager
from .models import (
    CatalogEntry,
    OperationResult,
    PluginSource,
    PluginView,
    RuntimePlugin,
    RuntimeState,
)

__all__ = [
    "PluginManager",
    "build_manager",
    "PluginManagerConfig",
    "PluginInstaller",
    "PipRunner",
    "CommandRunner",
    "EnablementStore",
    "EntryPointCatalog",
    "BootstrapReportProvider",
    "PluginCatalog",
    "ReportProvider",
    "CatalogEntry",
    "PluginView",
    "RuntimePlugin",
    "RuntimeState",
    "PluginSource",
    "OperationResult",
]
