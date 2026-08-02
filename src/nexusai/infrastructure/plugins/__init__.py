"""Plugin discovery, registration and lifecycle.

The compatibility rule itself lives in ``nexusai.domain.policy`` because it is
a decision, not an effect. This package holds only the machinery that applies it.
"""

from __future__ import annotations

from nexusai.infrastructure.plugins.discovery import (
    LoadReport,
    PluginDiscovery,
    RejectedPlugin,
)
from nexusai.infrastructure.plugins.lifecycle import plugin_lifecycle
from nexusai.infrastructure.plugins.registry import InMemoryPluginRegistry

__all__ = [
    "InMemoryPluginRegistry",
    "LoadReport",
    "PluginDiscovery",
    "RejectedPlugin",
    "plugin_lifecycle",
]
