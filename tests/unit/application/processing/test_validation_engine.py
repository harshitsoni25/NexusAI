"""Tests for the validation engine's merging behaviour."""

from __future__ import annotations

from nexusai.application.processing.validation import ValidationEngine
from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import ProcessedField, ProcessedRecord
from nexusai.infrastructure.validation.validators import (
    RequiredFieldsValidator,
    TypeValidator,
)
from nexusai.shared.types import JsonValue


def _record(**fields: JsonValue) -> ProcessedRecord:
    return ProcessedRecord(
        identity="r",
        raw=ExtractionResult(),
        fields={
            name: ProcessedField(name=name, value=value, raw_value=value)
            for name, value in fields.items()
        },
    )


def test_engine_merges_all_findings() -> None:
    engine = ValidationEngine(
        [RequiredFieldsValidator(["name", "price"]), TypeValidator({"price": (int, float)})]
    )
    result = engine.validate(_record(price="cheap"))
    codes = {issue.code for issue in result.issues}
    assert "missing-required-field" in codes
    assert "wrong-type" in codes


def test_engine_passes_clean_record() -> None:
    engine = ValidationEngine([RequiredFieldsValidator(["name"])])
    assert engine.validate(_record(name="X")).is_valid is True


def test_engine_with_no_validators_is_valid() -> None:
    assert ValidationEngine([]).validate(_record(name="X")).is_valid is True
