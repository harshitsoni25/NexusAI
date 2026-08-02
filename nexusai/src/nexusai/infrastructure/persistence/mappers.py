"""The mapper boundary between domain values and ORM rows.

Everything that crosses between the domain's value objects and the persistence
layer's SQLAlchemy rows passes through here, and nowhere else. Keeping the
translation in one module is what lets the domain stay ignorant of SQLAlchemy:
the repository speaks rows, the application speaks values, and the mapper is the
only code that knows both.

The mapping is intentionally explicit -- field by field -- rather than reflective,
so a schema change surfaces as a mapper change under review rather than as a
silent data shift.
"""

from __future__ import annotations

import json

from nexusai.domain.model.assessment import Severity, ValidationIssue
from nexusai.domain.model.persistence import DatasetId, DatasetVersion
from nexusai.domain.model.processing import ProcessedDataset, ProcessedRecord
from nexusai.domain.provenance.source import SourceReference
from nexusai.infrastructure.persistence.schema import (
    DatasetVersionRow,
    QualityMeasurementRow,
    RecordRow,
    SourceRow,
    ValidationIssueRow,
)


def dataset_version_to_row(version: DatasetVersion) -> DatasetVersionRow:
    """Map dataset-version metadata onto a fresh ORM row (without children)."""
    return DatasetVersionRow(
        dataset_id=str(version.dataset_id),
        version=version.version,
        run_id=version.run_id,
        processed_at=version.processed_at,
        content_hash=version.content_hash,
        record_count=version.record_count,
        quality_grade=version.quality_grade,
        configuration_ref=version.configuration_ref,
        source_count=version.source_count,
    )


def row_to_dataset_version(row: DatasetVersionRow) -> DatasetVersion:
    """Map an ORM row back to dataset-version metadata."""
    return DatasetVersion(
        dataset_id=DatasetId.of(row.dataset_id),
        version=row.version,
        run_id=row.run_id,
        processed_at=row.processed_at,
        content_hash=row.content_hash,
        record_count=row.record_count,
        quality_grade=row.quality_grade,
        configuration_ref=row.configuration_ref,
        source_count=row.source_count,
    )


def record_to_row(record: ProcessedRecord) -> RecordRow:
    """Map a processed record onto a row, serialising its payload as JSON.

    The full record dictionary -- processed fields, preserved raw values,
    validation and quality -- is stored so that loading a version reconstructs
    exactly what was persisted, keeping raw-to-processed traceability intact.
    """
    return RecordRow(
        identity=record.identity,
        payload=json.dumps(record.to_dict(), sort_keys=True, default=str),
    )


def record_row_to_dict(row: RecordRow) -> dict[str, object]:
    """Map a record row back to its stored dictionary."""
    loaded: dict[str, object] = json.loads(row.payload)
    return loaded


def issue_to_row(issue: ValidationIssue) -> ValidationIssueRow:
    """Map a validation issue onto a row."""
    return ValidationIssueRow(
        code=issue.code,
        message=issue.message,
        severity=issue.severity.name,
        location=issue.location,
    )


def row_to_issue(row: ValidationIssueRow) -> ValidationIssue:
    """Map a row back to a validation issue."""
    return ValidationIssue(
        code=row.code,
        message=row.message,
        severity=Severity[row.severity],
        location=row.location,
    )


def source_to_row(source: SourceReference) -> SourceRow:
    """Map a source reference onto a row."""
    return SourceRow(
        uri=source.uri,
        method=source.method,
        retrieved_at=source.retrieved_at,
        content_hash=source.content_hash,
    )


def row_to_source(row: SourceRow) -> SourceReference:
    """Map a row back to a source reference."""
    from datetime import UTC, datetime

    retrieved = row.retrieved_at or datetime.now(UTC)
    return SourceReference(
        uri=row.uri,
        retrieved_at=retrieved,
        method=row.method,
        content_hash=row.content_hash,
    )


def dataset_measurement_rows(dataset: ProcessedDataset) -> list[QualityMeasurementRow]:
    """Build quality-measurement rows from a dataset's context."""
    if dataset.context is None:
        return []
    return [
        QualityMeasurementRow(
            dimension=measurement.dimension,
            score=measurement.score,
            weight=measurement.weight,
        )
        for measurement in dataset.context.quality.measurements
    ]
