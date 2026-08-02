"""Response models for plugins."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PluginInfo(BaseModel):
    name: str
    kind: str | None = None
    status: str | None = None


class PluginReportModel(BaseModel):
    loaded: list[PluginInfo] = Field(default_factory=list)
    failed: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0
