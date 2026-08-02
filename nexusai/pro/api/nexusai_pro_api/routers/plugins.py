"""Plugins endpoint: report loaded plugins and load failures."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from nexusai_pro_api.dependencies import GatewayDep
from nexusai_pro_api.schemas.plugins import PluginInfo, PluginReportModel

router = APIRouter(prefix="/plugins", tags=["Plugins"])


def _coerce_plugins(registry: Any) -> list[PluginInfo]:
    infos: list[PluginInfo] = []
    try:
        for entry in list(registry):
            name = getattr(entry, "name", None) or str(entry)
            infos.append(PluginInfo(name=name, kind=getattr(entry, "kind", None)))
    except TypeError:
        pass
    return infos


@router.get("", response_model=PluginReportModel, summary="List plugins")
def list_plugins(gateway: GatewayDep) -> PluginReportModel:
    """Report the plugins the engine discovered at startup, and any load failures."""
    report = gateway.plugin_report()
    registry = gateway.plugin_registry()
    loaded = _coerce_plugins(registry)
    failed_raw = getattr(report, "failures", None) or getattr(report, "failed", None) or []
    failed = [{"detail": str(item)} for item in failed_raw]
    count = len(loaded) if loaded else len(registry) if hasattr(registry, "__len__") else 0
    return PluginReportModel(loaded=loaded, failed=failed, count=count)
