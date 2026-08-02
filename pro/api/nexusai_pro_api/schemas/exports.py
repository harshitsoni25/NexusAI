"""Request/response models for exports."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    dataset_id: str = Field(..., description="Dataset to export (latest stored version is used).")
    format: str = Field(
        ..., description="Export format, e.g. csv, json, ndjson.", examples=["ndjson"]
    )


class ExportManifestModel(BaseModel):
    dataset_id: str
    format: str
    location: str | None = Field(default=None, description="Where the export artifact was written.")
    record_count: int | None = None
