"""Response models for health."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Liveness(BaseModel):
    status: str = Field(default="ok")
    service: str = Field(default="nexusai-pro-api")


class Readiness(BaseModel):
    ready: bool
    checks: dict[str, Any] = Field(
        default_factory=dict, description="Engine doctor report, best-effort."
    )
