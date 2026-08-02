"""Tests for the processing models, especially raw immutability."""

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
from nexusai.domain.model.extraction import (
    ExtractedValue,
    ExtractionMethod,
    ExtractionResult,
    FieldProvenance,
)
from nexusai.domain.model.processing import (
    ProcessedDataset,
    ProcessedField,
    ProcessedRecord,
    ProcessingContext,
)
from nexusai.domain.model.quality import QualityGrade
from nexusai.shared.types import JsonValue


def _extraction(**values: JsonValue) -> ExtractionResult:
    prov = FieldProvenance(method=ExtractionMethod.CSS)
    return ExtractionResult(
        fields={
            name: ExtractedValue(value=value, provenance=prov) for name, value in values.items()
        }
    )


def _record(identity: str = "r", **fields: JsonValue) -> ProcessedRecord:
    return ProcessedRecord(
        identity=identity,
        raw=_extraction(**fields),
        fields={
            name: ProcessedField(name=name, value=value, raw_value=value)
            for name, value in fields.items()
        },
    )


def test_processed_field_preserves_raw() -> None:
    field = ProcessedField(
        name="price", value=19.99, raw_value=" $19.99 ", transformations=("whitespace", "numeric")
    )
    assert field.raw_value == " $19.99 "
    assert field.value == 19.99
    assert field.was_changed is True
    assert field.transformations == ("whitespace", "numeric")


def test_unchanged_field_reports_no_change() -> None:
    field = ProcessedField(name="name", value="X", raw_value="X")
    assert field.was_changed is False


def test_record_keeps_original_extraction_untouched() -> None:
    extraction = _extraction(price="$5")
    record = ProcessedRecord(
        identity="r",
        raw=extraction,
        fields={"price": ProcessedField(name="price", value=5, raw_value="$5")},
    )
    # The processed value is the transformed number...
    assert record.value("price") == 5
    # ...but the raw extraction still holds the original string, unchanged.
    assert record.raw is extraction
    assert record.raw.value("price") == "$5"


def test_record_value_of_absent_field_is_none() -> None:
    assert _record().value("missing") is None


def test_with_validation_returns_new_record() -> None:
    record = _record(name="X")
    result = ValidationResult(
        issues=[ValidationIssue(code="c", message="m", severity=Severity.ERROR)]
    )
    updated = record.with_validation(result)
    assert updated is not record
    assert updated.validation.is_valid is False
    assert record.validation.is_valid is True  # original untouched


def test_with_quality_returns_new_record() -> None:
    record = _record(name="X")
    quality = QualityResult(measurements=(QualityMeasurement(dimension="d", score=0.5),))
    updated = record.with_quality(quality)
    assert updated is not record
    assert updated.quality.composite_score == 0.5
    assert record.quality.composite_score == 0.0


def test_dataset_validity_reflects_records() -> None:
    good = _record("a", name="X")
    bad = _record("b", name="Y").with_validation(
        ValidationResult(issues=[ValidationIssue(code="c", message="m")])
    )
    assert ProcessedDataset(records=[good]).is_valid is True
    assert ProcessedDataset(records=[good, bad]).is_valid is False


def test_dataset_with_context_and_len() -> None:
    dataset = ProcessedDataset(records=[_record("a"), _record("b")])
    context = ProcessingContext(
        processed_at=datetime(2026, 1, 1, tzinfo=UTC), framework_version="0.1.0"
    )
    with_ctx = dataset.with_context(context)
    assert len(with_ctx) == 2
    assert with_ctx.context is context
    assert dataset.context is None


def test_processing_context_serialises() -> None:
    context = ProcessingContext(
        processed_at=datetime(2026, 1, 1, tzinfo=UTC),
        framework_version="0.1.0",
        rule_version="v3",
        quality_grade=QualityGrade.B,
        change_summary=ChangeSummary(added=1),
    )
    payload = context.to_dict()
    assert payload["framework_version"] == "0.1.0"
    assert payload["rule_version"] == "v3"
    assert payload["quality_grade"] == "B"
    assert payload["change_summary"]["added"] == 1


def test_record_serialisation_includes_raw() -> None:
    record = ProcessedRecord(
        identity="r",
        raw=_extraction(price="$5"),
        fields={"price": ProcessedField(name="price", value=5, raw_value="$5")},
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    payload = record.to_dict()
    assert payload["identity"] == "r"
    assert payload["fields"]["price"]["raw_value"] == "$5"
    assert payload["raw"]["fields"]["price"]["value"] == "$5"
    assert payload["retrieved_at"].startswith("2026-01-01")
