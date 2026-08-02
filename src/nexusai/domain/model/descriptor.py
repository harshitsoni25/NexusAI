"""A descriptor unifying what the framework knows about one plugin.

``PluginMetadata`` is what a plugin says about itself. ``PluginDescriptor`` is
what the *framework* knows about it: the metadata, where it was discovered, and
its lifecycle state. The two are complementary -- metadata is self-description,
the descriptor is the framework's record of a known plugin -- and keeping them
separate means the framework's bookkeeping never has to be smuggled into the
plugin author's declaration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from nexusai.domain.model.plugin import PluginMetadata
from nexusai.shared.lifecycle import LifecycleState


class PluginState(Enum):
    """The framework's view of where a plugin is in its life.

    Distinct from :class:`~nexusai.shared.lifecycle.LifecycleState`, which
    tracks a component's own init/dispose phase. This adds the states that only
    the framework can know: a plugin can be discovered but not yet registered, or
    rejected outright.
    """

    DISCOVERED = "discovered"
    REGISTERED = "registered"
    INITIALISED = "initialised"
    DISPOSED = "disposed"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True, kw_only=True)
class PluginDescriptor:
    """The framework's record of a single known plugin.

    Attributes:
        metadata: The plugin's self-description.
        origin: Where it was found -- an entry-point reference or an allow-list
            spec. Recorded so that "which of the three installed distributions
            provided this?" has an answer.
        state: The framework's view of its lifecycle.
        detail: Supporting information, such as a rejection reason.
    """

    metadata: PluginMetadata
    origin: str
    state: PluginState = PluginState.DISCOVERED
    detail: str = ""

    @property
    def qualified_name(self) -> str:
        """The plugin's globally unique ``extension_point:name`` identifier."""
        return self.metadata.qualified_name

    @property
    def is_active(self) -> bool:
        """Whether the plugin is registered and not yet disposed."""
        return self.state in {PluginState.REGISTERED, PluginState.INITIALISED}

    def in_state(self, state: PluginState, *, detail: str = "") -> PluginDescriptor:
        """Return a copy advanced to ``state``, optionally with ``detail``."""
        return PluginDescriptor(
            metadata=self.metadata,
            origin=self.origin,
            state=state,
            detail=detail or self.detail,
        )

    @classmethod
    def from_lifecycle(cls, state: LifecycleState) -> PluginState:
        """Map a component lifecycle state onto the framework's plugin state."""
        return {
            LifecycleState.CREATED: PluginState.REGISTERED,
            LifecycleState.INITIALISED: PluginState.INITIALISED,
            LifecycleState.DISPOSED: PluginState.DISPOSED,
        }[state]

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "metadata": self.metadata_dict(),
            "origin": self.origin,
            "state": self.state.value,
            "detail": self.detail,
        }

    def metadata_dict(self) -> dict[str, Any]:
        """Return the plugin metadata as serialisable data."""
        return {
            "name": self.metadata.name,
            "version": self.metadata.version,
            "extension_point": self.metadata.extension_point.value,
            "api_version": str(self.metadata.api_version),
            "description": self.metadata.description,
            "author": self.metadata.author,
        }
