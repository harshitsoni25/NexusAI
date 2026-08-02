"""Shared builders for Phase 7 application-layer tests."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from nexusai.domain.model.checkpoint import Checkpoint
from nexusai.domain.model.extraction import (
    ExtractedValue,
    ExtractionMethod,
    ExtractionResult,
    FieldProvenance,
)
from nexusai.domain.model.job import Job
from nexusai.domain.model.processing import (
    ProcessedDataset,
    ProcessedField,
    ProcessedRecord,
)
from nexusai.domain.model.retrieval import Document
from nexusai.domain.provenance.source import SourceReference

_PROVENANCE = FieldProvenance(method=ExtractionMethod.CSS)


def make_document(
    url: str = "https://shop.example.com/", body: bytes = b"<html></html>"
) -> Document:
    """Build a document with the given URL and body."""
    return Document(
        url=url,
        content=body,
        status_code=200,
        provider="fixture",
        retrieved_at=datetime.now(UTC),
        media_type="text/html",
    )


def make_extraction(name: str = "Widget", price: str = "9.99") -> ExtractionResult:
    """Build a single extraction result with name and price fields."""
    return ExtractionResult(
        fields={
            "name": ExtractedValue(value=name, provenance=_PROVENANCE),
            "price": ExtractedValue(value=price, provenance=_PROVENANCE),
        }
    )


def make_dataset(count: int = 2) -> ProcessedDataset:
    """Build a small processed dataset with a source reference."""
    source = SourceReference(
        uri="https://shop.example.com/", retrieved_at=datetime.now(UTC), method="http-get"
    )
    records = [
        ProcessedRecord(
            identity=f"p{index}",
            raw=make_extraction(),
            source=source,
            fields={
                "name": ProcessedField(name="name", value="Widget", raw_value="Widget"),
                "price": ProcessedField(name="price", value=9.99, raw_value="9.99"),
            },
        )
        for index in range(count)
    ]
    return ProcessedDataset(records=records)


class MemoryJobStore:
    """An in-memory job store for tests."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def save(self, job: Job) -> None:
        self._jobs[job.job_id] = job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list(self, *, limit: int = 100) -> Sequence[Job]:
        return list(self._jobs.values())[:limit]


class MemoryCheckpointStore:
    """An in-memory, append-only checkpoint store for tests."""

    def __init__(self) -> None:
        self._checkpoints: list[Checkpoint] = []

    def save(self, checkpoint: Checkpoint) -> None:
        self._checkpoints.append(checkpoint)

    def latest(self, job_id: str) -> Checkpoint | None:
        for checkpoint in reversed(self._checkpoints):
            if checkpoint.job_id == job_id:
                return checkpoint
        return None
