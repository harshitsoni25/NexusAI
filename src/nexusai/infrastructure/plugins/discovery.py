"""Plugin discovery.

Two mechanisms, deliberately no third. Installed distributions advertise plugins
through Python entry points, which makes the plugin set explicit, visible to
packaging tools and managed as a dependency. An explicit allow-list of
``module:attribute`` paths covers local development and private plugins that are
not packaged for distribution.

Scanning directories for Python files is not supported, and that is a decision
rather than an omission (ADR-0006). It executes untrusted code found on disk,
which is a security defect in a system intended to run unattended, and it makes
the effective plugin set depend on filesystem state rather than on declared
configuration.

Discovery is passive: importing a plugin module must not perform work or mutate
global state. All setup belongs in ``Plugin.initialize``.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from importlib import metadata as importlib_metadata

from nexusai.domain.errors import PluginContractError, PluginError, PluginLoadError
from nexusai.domain.model.plugin import PluginMetadata
from nexusai.domain.policy.plugin_compatibility import assert_compatible
from nexusai.domain.ports.observability import Logger
from nexusai.domain.ports.plugins import Plugin
from nexusai.infrastructure.config.settings import PluginSettings
from nexusai.infrastructure.plugins.registry import InMemoryPluginRegistry


@dataclass(frozen=True, slots=True)
class RejectedPlugin:
    """A candidate that was found but not registered."""

    reference: str
    reason: str

    def __str__(self) -> str:
        return f"{self.reference}: {self.reason}"


@dataclass(frozen=True, slots=True)
class LoadReport:
    """The outcome of a discovery pass.

    Rejections are data rather than exceptions because one broken third-party
    plugin must not prevent the framework from starting. The report is surfaced
    by ``nexusai plugins list`` and recorded against the run, so a rejection
    is visible rather than silent.
    """

    accepted: tuple[PluginMetadata, ...] = ()
    rejected: tuple[RejectedPlugin, ...] = ()

    @property
    def has_failures(self) -> bool:
        """Whether any candidate was rejected."""
        return bool(self.rejected)

    def summary(self) -> str:
        """One-line summary for logs."""
        return f"{len(self.accepted)} plugin(s) loaded, {len(self.rejected)} rejected"


@dataclass(frozen=True, slots=True)
class PluginDiscovery:
    """Finds plugins and registers the ones that pass every gate.

    Args:
        settings: Discovery configuration.
        logger: Receives one record per rejection, so failures are never silent.
    """

    settings: PluginSettings
    logger: Logger

    def discover(self, registry: InMemoryPluginRegistry) -> LoadReport:
        """Populate ``registry`` with every valid, enabled plugin.

        Raises:
            PluginError: Only when ``fail_on_load_error`` is enabled and at least
                one candidate was rejected.
        """
        if not self.settings.discovery_enabled:
            self.logger.debug("Plugin discovery is disabled by configuration")
            return LoadReport()

        accepted: list[PluginMetadata] = []
        rejected: list[RejectedPlugin] = []
        for reference, factory in self._candidates():
            outcome = self._admit(reference, factory, registry)
            if isinstance(outcome, PluginMetadata):
                accepted.append(outcome)
            elif outcome is not None:
                rejected.append(outcome)

        report = LoadReport(tuple(accepted), tuple(rejected))
        self.logger.info("Plugin discovery complete", **{"summary": report.summary()})
        if report.has_failures and self.settings.fail_on_load_error:
            raise PluginError(
                "One or more plugins failed to load and fail_on_load_error is enabled",
                rejected=tuple(str(item) for item in report.rejected),
            )
        return report

    def _candidates(self) -> Iterator[tuple[str, object]]:
        """Yield ``(reference, factory)`` pairs from both discovery mechanisms."""
        yield from self._from_entry_points()
        yield from self._from_allowlist()

    def _from_entry_points(self) -> Iterator[tuple[str, object]]:
        for entry_point in importlib_metadata.entry_points(group=self.settings.entry_point_group):
            reference = f"{self.settings.entry_point_group}:{entry_point.name}"
            try:
                yield reference, entry_point.load()
            except Exception as exc:  # noqa: BLE001 - a bad plugin must not stop discovery
                self.logger.warning(
                    "Plugin entry point could not be loaded",
                    reference=reference,
                    error=str(exc),
                )
                yield reference, _FailedImport(str(exc))

    def _from_allowlist(self) -> Iterator[tuple[str, object]]:
        for spec in self.settings.allowlist:
            try:
                yield spec, _import_object(spec)
            except PluginLoadError as exc:
                yield spec, _FailedImport(exc.message)

    def _admit(
        self, reference: str, factory: object, registry: InMemoryPluginRegistry
    ) -> PluginMetadata | RejectedPlugin | None:
        """Apply every gate to one candidate.

        Returns:
            The metadata of an accepted plugin, a rejection, or ``None`` when the
            candidate was disabled by configuration and should not be reported as
            a failure.
        """
        if isinstance(factory, _FailedImport):
            return self._reject(reference, factory.reason)
        try:
            plugin = factory() if callable(factory) else factory
        except Exception as exc:  # noqa: BLE001 - third-party constructor
            return self._reject(reference, f"constructor raised {type(exc).__name__}: {exc}")

        if not isinstance(plugin, Plugin):
            return self._reject(
                reference,
                "does not satisfy the plugin contract (needs metadata, initialize and dispose)",
            )
        try:
            # Typed as ``object`` deliberately: the protocol promises a
            # PluginMetadata, but a third-party plugin is not obliged to keep
            # that promise, and this is the boundary where it is checked.
            declared: object = plugin.metadata
        except Exception as exc:  # noqa: BLE001 - third-party property
            return self._reject(reference, f"metadata raised {type(exc).__name__}: {exc}")
        if not isinstance(declared, PluginMetadata):
            return self._reject(reference, "metadata is not a PluginMetadata instance")
        metadata = declared

        if (
            metadata.name in self.settings.disabled
            or metadata.qualified_name in self.settings.disabled
        ):
            self.logger.debug("Plugin disabled by configuration", plugin=metadata.qualified_name)
            return None

        try:
            assert_compatible(metadata)
            registry.register(plugin)
        except (PluginContractError, PluginError) as exc:
            return self._reject(reference, exc.message)
        return metadata

    def _reject(self, reference: str, reason: str) -> RejectedPlugin:
        self.logger.warning("Plugin rejected", reference=reference, reason=reason)
        return RejectedPlugin(reference, reason)


@dataclass(frozen=True, slots=True)
class _FailedImport:
    """Marker for a candidate that could not be imported."""

    reason: str


def _import_object(spec: str) -> object:
    """Resolve a ``module:attribute`` specification to an object.

    Raises:
        PluginLoadError: If the specification is malformed, the module cannot be
            imported, or the attribute does not exist.
    """
    module_path, separator, attribute = spec.partition(":")
    if not separator or not module_path or not attribute:
        raise PluginLoadError(
            "Plugin allow-list entries must use the form 'module:attribute'", entry=spec
        )
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise PluginLoadError(
            "Plugin module could not be imported", entry=spec, error=str(exc)
        ) from exc
    try:
        return getattr(module, attribute)
    except AttributeError as exc:
        raise PluginLoadError(
            "Plugin module does not define this attribute", entry=spec, error=str(exc)
        ) from exc


def entry_point_group_of(settings: PluginSettings) -> str:
    """Return the entry point group plugins should advertise themselves under."""
    return settings.entry_point_group


def rejected_references(report: LoadReport) -> Sequence[str]:
    """Return the references of every rejected candidate, for reporting."""
    return [item.reference for item in report.rejected]
