"""Enable/disable state for plugins.

The engine discovers every installed plugin; whether a plugin should be *used* is a
management decision the Pro layer owns. This store persists which plugins are disabled
(a small JSON file) and can filter a set of plugin ids down to the enabled ones. It
does not change engine discovery — Pro consumers honour ``effective`` membership.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path


class EnablementStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._disabled: set[str] = set()
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._disabled = set(data.get("disabled", []))
        except (FileNotFoundError, json.JSONDecodeError):
            self._disabled = set()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({"disabled": sorted(self._disabled)}, indent=2), encoding="utf-8")

    def is_enabled(self, plugin_id: str) -> bool:
        with self._lock:
            return plugin_id not in self._disabled

    def set_enabled(self, plugin_id: str, enabled: bool) -> None:
        with self._lock:
            if enabled:
                self._disabled.discard(plugin_id)
            else:
                self._disabled.add(plugin_id)
            self._save()

    def forget(self, plugin_id: str) -> None:
        """Drop any stored state for a plugin (used when it is removed)."""
        with self._lock:
            if plugin_id in self._disabled:
                self._disabled.discard(plugin_id)
                self._save()

    def disabled_ids(self) -> set[str]:
        with self._lock:
            return set(self._disabled)

    def filter_enabled(self, ids: list[str]) -> list[str]:
        with self._lock:
            return [i for i in ids if i not in self._disabled]
