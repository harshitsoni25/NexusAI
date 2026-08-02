"""Plugin manager configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _default_state_path() -> Path:
    root = os.environ.get("NEXUSAI_PRO_STATE_DIR")
    base = Path(root) if root else Path.home() / ".nexusai-pro"
    return base / "plugins" / "enablement.json"


@dataclass(slots=True)
class PluginManagerConfig:
    entry_point_group: str = os.environ.get("NEXUSAI_PLUGIN_GROUP", "nexusai.plugins")
    enablement_path: Path = field(default_factory=_default_state_path)
