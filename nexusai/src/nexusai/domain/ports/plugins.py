"""Ports describing what a plugin is and how one is looked up."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from nexusai.domain.model.plugin import ExtensionPoint, PluginMetadata


@runtime_checkable
class Plugin(Protocol):
    """The contract every plugin satisfies, whatever it extends.

    Category-specific behaviour is declared by the contract for each extension
    point and introduced alongside the engine that consumes it. This protocol
    covers only what is common: self-description and lifecycle.
    """

    @property
    def metadata(self) -> PluginMetadata:
        """Self-description used for registration, reporting and diagnostics."""
        ...

    def initialize(self) -> None:
        """Acquire resources. Called once per run, after registration.

        Importing a plugin module must not do work; all setup belongs here, so
        that discovery stays cheap and side-effect free.
        """
        ...

    def dispose(self) -> None:
        """Release resources. Called once at the end of a run.

        Must be safe to call even if :meth:`initialize` failed, and must not
        raise: a disposal failure is logged, never allowed to mask the outcome
        of the run itself.
        """
        ...


@runtime_checkable
class PluginRegistry(Protocol):
    """Read access to the plugins registered for the current run."""

    def get(self, extension_point: ExtensionPoint, name: str) -> Plugin:
        """Return the named plugin.

        Raises:
            PluginError: If no plugin is registered under that name.
        """
        ...

    def all_for(self, extension_point: ExtensionPoint) -> Sequence[Plugin]:
        """Return every plugin registered for ``extension_point``."""
        ...

    def has(self, extension_point: ExtensionPoint, name: str) -> bool:
        """Whether a plugin is registered under that name."""
        ...
