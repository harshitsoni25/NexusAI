"""Fixtures for Phase 6 downstream tests: datasets, stores and output dirs."""

from __future__ import annotations

from datetime import UTC, datetime

from nexusai.domain.model.assessment import (
    QualityMeasurement,
    QualityResult,
    Severity,
    ValidationIssue,
    ValidationResult,
)
from nexusai.domain.model.change import ChangeSummary
from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import (
    ProcessedDataset,
    ProcessedField,
    ProcessedRecord,
    ProcessingContext,
)
from nexusai.domain.model.quality import QualityGrade
from nexusai.domain.provenance.source import SourceReference
from nexusai.shared.types import JsonValue


def make_record(identity: str, name: str, price: JsonValue, uri: str) -> ProcessedRecord:
    """Build a processed record with a source and two fields."""
    source = SourceReference(
        uri=uri, retrieved_at=datetime(2025, 1, 1, tzinfo=UTC), method="http-get"
    )
    valid = (
        ValidationResult()
        if price is not None
        else ValidationResult(
            issues=[ValidationIssue(code="missing", message="no price", severity=Severity.WARNING)]
        )
    )
    return ProcessedRecord(
        identity=identity,
        raw=ExtractionResult(),
        source=source,
        validation=valid,
        fields={
            "name": ProcessedField(name="name", value=name, raw_value=name),
            "price": ProcessedField(name="price", value=price, raw_value=str(price)),
        },
    )


def make_dataset(*, count: int = 2) -> ProcessedDataset:
    """Build a small processed dataset with a full processing context."""
    records = [
        make_record(f"p{i}", f"Item {i}", (i * 10) if i else None, f"https://shop/p{i}")
        for i in range(count)
    ]
    context = ProcessingContext(
        processed_at=datetime(2025, 1, 2, tzinfo=UTC),
        framework_version="0.1.0",
        rule_version="rules-v2",
        validation_summary=ValidationResult(
            issues=[
                ValidationIssue(
                    code="missing_price",
                    message="price absent",
                    severity=Severity.WARNING,
                    location="price",
                )
            ]
        ),
        quality=QualityResult(
            measurements=[
                QualityMeasurement(dimension="completeness", score=0.9, weight=2.0),
                QualityMeasurement(dimension="accuracy", score=0.5, weight=1.0),
            ]
        ),
        quality_grade=QualityGrade.B,
        change_summary=ChangeSummary(added=2, removed=1, modified=0, detectors=["content-hash"]),
        sources=[
            SourceReference(
                uri="https://shop/p1",
                retrieved_at=datetime(2025, 1, 1, tzinfo=UTC),
                method="http-get",
            )
        ],
    )
    return ProcessedDataset(records=records, context=context)
