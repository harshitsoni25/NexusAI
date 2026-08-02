"""Request/response models for scraping."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScrapeRequest(BaseModel):
    target: str = Field(..., description="URL or target identifier to scrape.", examples=["https://example.com"])
    dataset_id: str | None = Field(
        default=None, description="Dataset to write into; a stable id is derived from the target when omitted."
    )
    export_formats: list[str] = Field(
        default_factory=lambda: ["csv", "json"], description="Export formats produced by the workflow."
    )
    report_formats: list[str] = Field(
        default_factory=lambda: ["html", "json"], description="Report formats produced by the workflow."
    )


class ResumeRequest(BaseModel):
    target: str = Field(..., description="Original target of the job being resumed.")
    dataset_id: str = Field(..., description="Dataset id of the job being resumed.")
    export_formats: list[str] = Field(default_factory=lambda: ["csv", "json"])
    report_formats: list[str] = Field(default_factory=lambda: ["html", "json"])


class ScrapeAccepted(BaseModel):
    submission_id: str = Field(..., description="Identifier for this accepted submission.")
    state: str = Field(..., description="accepted | running | finished | failed")
    target: str
    dataset_id: str
    job_id: str | None = Field(default=None, description="Engine job id, present once the scrape starts/finishes.")
    status_url: str = Field(..., description="Poll this URL for submission progress.")
