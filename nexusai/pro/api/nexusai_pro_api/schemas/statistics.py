"""Response models for statistics."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StatisticsModel(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict, description="Engine-computed statistics.")

    @classmethod
    def from_engine(cls, stats: Any) -> StatisticsModel:
        to_dict = getattr(stats, "to_dict", None)
        return cls(data=to_dict() if callable(to_dict) else {"value": str(stats)})
