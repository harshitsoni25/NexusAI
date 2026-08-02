"""Deterministic site-adapter resolution.

A site adapter teaches the generic engine how to scrape one target. Resolution
picks which adapter handles a given target, and it must be deterministic: an
explicit choice always wins, otherwise the registered adapters are matched
against the target, and a configured default is the fallback. What it must never
do is choose silently between two adapters that both claim a target -- an
ambiguous match is an error the operator resolves, not a coin the framework
flips.
"""

from __future__ import annotations

from collections.abc import Sequence

from nexusai.domain.errors.exceptions import NexusAIError
from nexusai.domain.ports.application import SiteAdapter


class AdapterResolutionError(NexusAIError):
    """No adapter, or more than one, matched a target with no way to choose."""


class AdapterRegistry:
    """A small registry of site adapters with deterministic resolution."""

    def __init__(self, adapters: Sequence[SiteAdapter] = ()) -> None:
        self._adapters: dict[str, SiteAdapter] = {a.name: a for a in adapters}

    def register(self, adapter: SiteAdapter) -> None:
        """Register ``adapter`` under its name."""
        self._adapters[adapter.name] = adapter

    def names(self) -> list[str]:
        """Return the registered adapter names, sorted."""
        return sorted(self._adapters)

    def resolve(
        self, target: str, *, explicit: str | None = None, default: str | None = None
    ) -> SiteAdapter:
        """Resolve the adapter for ``target``.

        Order: an ``explicit`` name wins; otherwise adapters whose
        :meth:`matches` accepts the target are considered, and exactly one must
        match; otherwise a ``default`` adapter is used if configured.

        Raises:
            AdapterResolutionError: If the explicit or default adapter is unknown,
                or if zero or several adapters match with no default.
        """
        if explicit is not None:
            adapter = self._adapters.get(explicit)
            if adapter is None:
                raise AdapterResolutionError("Unknown site adapter", requested=explicit)
            return adapter

        matches = [a for a in self._adapters.values() if a.matches(target)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise AdapterResolutionError(
                "Several site adapters match the target; select one explicitly",
                target=target,
                candidates=", ".join(sorted(a.name for a in matches)),
            )

        if default is not None:
            adapter = self._adapters.get(default)
            if adapter is None:
                raise AdapterResolutionError("Unknown default adapter", requested=default)
            return adapter
        raise AdapterResolutionError("No site adapter matched the target", target=target)
