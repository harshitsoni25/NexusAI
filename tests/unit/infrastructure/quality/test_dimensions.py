"""Tests for the six data-quality dimensions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from nexusai.domain.model.assessment import Severity, ValidationIssue, ValidationResult
from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import (
    ProcessedDataset,
    ProcessedField,
    ProcessedRecord,
)
from nexusai.infrastructure.quality.dimensions import (
    AccuracyDimension,
    CompletenessDimension,
    ConsistencyDimension,
    IntegrityDimension,
    TimelinessDimension,
    UniquenessDimension,
)
from nexusai.shared.types import JsonValue

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _record(
    identity: str, *, valid: bool = True, retrieved: datetime | None = None, **fields: JsonValue
) -> ProcessedRecord:
    validation = (
        ValidationResult()
        if valid
        else ValidationResult(
            issues=[ValidationIssue(code="c", message="m", severity=Severity.ERROR)]
        )
    )
    return ProcessedRecord(
        identity=identity,
        raw=ExtractionResult(),
        validation=validation,
        retrieved_at=retrieved,
        fields={
            name: ProcessedField(name=name, value=value, raw_value=value)
            for name, value in fields.items()
        },
    )


def test_completeness_counts_present_values() -> None:
    dataset = ProcessedDataset(records=[_record("a", name="X", price=1), _record("b", name="Y")])
    measurement = CompletenessDimension(["name", "price"]).assess(dataset)
    assert measurement.score == 0.75
    assert measurement.detail["present"] == 3


def test_completeness_of_empty_is_one() -> None:
    assert CompletenessDimension(["x"]).assess(ProcessedDataset()).score == 1.0


def test_accuracy_is_fraction_valid() -> None:
    dataset = ProcessedDataset(records=[_record("a", valid=True), _record("b", valid=False)])
    assert AccuracyDimension().assess(dataset).score == 0.5


def test_consistency_penalises_mixed_types() -> None:
    dataset = ProcessedDataset(
        records=[_record("a", price=1), _record("b", price=2), _record("c", price="3")]
    )
    measurement = ConsistencyDimension(["price"]).assess(dataset)
    assert round(measurement.score, 3) == 0.667


def test_uniqueness_detects_duplicates() -> None:
    dataset = ProcessedDataset(records=[_record("a"), _record("a"), _record("b")])
    assert round(UniquenessDimension().assess(dataset).score, 3) == 0.667


def test_integrity_requires_key_fields() -> None:
    dataset = ProcessedDataset(records=[_record("a", key="present"), _record("b")])
    assert IntegrityDimension(["key"]).assess(dataset).score == 0.5


def test_timeliness_fresh_and_stale() -> None:
    dataset = ProcessedDataset(
        records=[
            _record("a", retrieved=_NOW),
            _record("b", retrieved=_NOW - timedelta(days=10)),
            _record("c", retrieved=None),
        ]
    )
    measurement = TimelinessDimension(_NOW, max_age_seconds=86400).assess(dataset)
    assert round(measurement.score, 3) == 0.333


def test_dimensions_of_empty_dataset_score_one() -> None:
    empty = ProcessedDataset()
    assert AccuracyDimension().assess(empty).score == 1.0
    assert UniquenessDimension().assess(empty).score == 1.0
    assert TimelinessDimension(_NOW, max_age_seconds=1).assess(empty).score == 1.0
    assert IntegrityDimension(["k"]).assess(empty).score == 1.0


def test_consistency_skips_fields_with_no_values() -> None:
    # Field never present across records -> contributes nothing, score stays 1.0.
    dataset = ProcessedDataset(records=[_record("a", other=1), _record("b", other=2)])
    assert ConsistencyDimension(["absent"]).assess(dataset).score == 1.0
