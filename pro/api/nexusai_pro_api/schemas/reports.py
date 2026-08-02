"""Request/response models for reports."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReportRequest(BaseModel):
    dataset_id: str = Field(..., description="Dataset to report on (latest stored version is used).")
    format: str = Field(..., description="Report format, e.g. html, json.", examples=["html"])


class ReportManifestModel(BaseModel):
    dataset_id: str
    format: str
    location: str | None = Field(default=None, description="Where the report artifact was written.")
