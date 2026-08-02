"""Models for the Nexus AI Pro plugin manager.

This layer does not redefine what a plugin is — that lives in the engine
(``nexusai.domain.ports.plugins``). These are management-view records: a plugin's
installable distribution, its runtime state as reported by the engine's discovery, and
the outcome of a lifecycle operation. Enablement is the one piece of state the manager
owns, layered on top of the engine's discovery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PluginSource(str, Enum):
    ENTRY_POINT = "entry_point"
    ALLOWLIST = "allowlist"


class RuntimeState(str, Enum):
    LOADED = "loaded"  # accepted by the engine's discovery
    REJECTED = "rejected"  # discovered but rejected (bad contract, import error, ...)
    NOT_LOADED = "not_loaded"  # present as a distribution but not accepted


@dataclass(slots=True)
class RuntimePlugin:
    """The engine's self-reported metadata for a plugin (mirrors PluginMetadata)."""

    name: str
    version: str
    api_version: str
    extension_point: str
    description: str | None = None


@dataclass(slots=True)
class CatalogEntry:
    """One plugin as seen by the catalog: distribution + runtime facts."""

    id: str
    source: PluginSource
    distribution: str | None
    distribution_version: str | None
    state: RuntimeState
    runtime: RuntimePlugin | None = None
    reason: str | None = None  # rejection reason, when state is REJECTED


@dataclass(slots=True)
class PluginView:
    """A catalog entry enriched with the manager's enablement state."""

    id: str
    enabled: bool
    source: PluginSource
    state: RuntimeState
    distribution: str | None
    distribution_version: str | None
    runtime: RuntimePlugin | None = None
    reason: str | None = None

    @property
    def active(self) -> bool:
        """Enabled *and* accepted by the engine."""
        return self.enabled and self.state is RuntimeState.LOADED


@dataclass(slots=True)
class OperationResult:
    """The outcome of an install/update/remove/enable/disable operation."""

    ok: bool
    action: str
    target: str
    message: str = ""
    stdout: str = ""
    stderr: str = ""
    details: dict[str, str] = field(default_factory=dict)
