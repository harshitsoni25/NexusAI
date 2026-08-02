"""The plugin catalog — the read side, built entirely on the engine's own data.

``EntryPointCatalog`` reuses two facts the engine already exposes:

  * the engine's ``LoadReport`` (via ``container.plugin_report``), which says which
    plugins were **accepted** and which were **rejected** and why; and
  * the ``nexusai.plugins`` entry points registered by installed distributions,
    read with ``importlib.metadata`` — giving each plugin's pip distribution and
    version for lifecycle and version management.

It correlates the two by loading each entry point's ``Plugin.metadata()`` (the engine's
own plugin protocol) so a plugin's runtime name/version lines up with the distribution
that provides it. Nothing about the plugin system is redefined here.
"""

from __future__ import annotations

import importlib.metadata as importlib_metadata
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from nexusai.infrastructure.plugins.discovery import LoadReport

from .models import CatalogEntry, PluginSource, RuntimePlugin, RuntimeState


class ReportProvider(Protocol):
    """Supplies the engine's discovery report. The default bootstraps the engine."""

    def accepted_by_name(self) -> dict[str, RuntimePlugin]: ...
    def rejected_by_reference(self) -> dict[str, str]: ...


class BootstrapReportProvider:
    """Runs the engine's real discovery and adapts its ``LoadReport``."""

    def __init__(self, *, config_file: Path | None = None) -> None:
        self._config_file = config_file

    def _report(self) -> LoadReport:
        from nexusai.composition.container import bootstrap

        container = bootstrap(config_file=self._config_file)
        return container.plugin_report

    def accepted_by_name(self) -> dict[str, RuntimePlugin]:
        report = self._report()
        result: dict[str, RuntimePlugin] = {}
        for md in report.accepted:
            result[md.name] = RuntimePlugin(
                name=md.name,
                version=str(md.version),
                api_version=str(getattr(md, "api_version", "")),
                extension_point=getattr(getattr(md, "extension_point", None), "value", ""),
                description=getattr(md, "description", None),
            )
        return result

    def rejected_by_reference(self) -> dict[str, str]:
        report = self._report()
        return {item.reference: item.reason for item in report.rejected}


class PluginCatalog(Protocol):
    def entries(self) -> list[CatalogEntry]: ...


class EntryPointCatalog:
    """Builds catalog entries from installed entry points + the engine report."""

    def __init__(self, report_provider: ReportProvider, *, group: str = "nexusai.plugins") -> None:
        self._reports = report_provider
        self._group = group

    def entries(self) -> list[CatalogEntry]:
        accepted = self._reports.accepted_by_name()
        rejected = self._reports.rejected_by_reference()
        entries: list[CatalogEntry] = []

        for ep in importlib_metadata.entry_points(group=self._group):
            dist = getattr(ep, "dist", None)
            dist_name = getattr(dist, "name", None)
            dist_version = getattr(dist, "version", None)
            reference = f"{self._group}:{ep.name}"

            runtime, state, reason = self._resolve(ep, reference, accepted, rejected)
            entries.append(
                CatalogEntry(
                    id=runtime.name if runtime else ep.name,
                    source=PluginSource.ENTRY_POINT,
                    distribution=dist_name,
                    distribution_version=dist_version,
                    state=state,
                    runtime=runtime,
                    reason=reason,
                )
            )
        return entries

    def _resolve(
        self,
        ep: object,
        reference: str,
        accepted: dict[str, RuntimePlugin],
        rejected: dict[str, str],
    ) -> tuple[RuntimePlugin | None, RuntimeState, str | None]:
        if reference in rejected:
            return None, RuntimeState.REJECTED, rejected[reference]
        try:
            factory = ep.load()  # type: ignore[attr-defined]
            plugin = factory() if callable(factory) else factory
            md = plugin.metadata
            name = getattr(md, "name", None)
        except Exception as exc:  # noqa: BLE001 - a broken plugin is reported, not raised
            return None, RuntimeState.REJECTED, f"{type(exc).__name__}: {exc}"

        if name in accepted:
            return accepted[name], RuntimeState.LOADED, None
        # Loadable but the engine did not accept it (e.g. disabled by config).
        return (
            RuntimePlugin(
                name=str(name),
                version=str(getattr(md, "version", "")),
                api_version=str(getattr(md, "api_version", "")),
                extension_point=getattr(getattr(md, "extension_point", None), "value", ""),
                description=getattr(md, "description", None),
            ),
            RuntimeState.NOT_LOADED,
            None,
        )
