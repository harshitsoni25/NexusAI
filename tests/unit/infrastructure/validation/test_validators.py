"""Tests for the structural validators."""

from __future__ import annotations

from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import ProcessedField, ProcessedRecord
from nexusai.infrastructure.validation.validators import (
    CollectionValidator,
    FormatValidator,
    NestedObjectValidator,
    NonEmptyRecordValidator,
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


def test_required_fields_flags_missing() -> None:
    result = RequiredFieldsValidator(["name", "price"]).validate(_record(name="X"))
    assert result.is_valid is False
    assert result.issues[0].location == "price"


def test_required_fields_treats_blank_as_missing() -> None:
    result = RequiredFieldsValidator(["name"]).validate(_record(name="  "))
    assert result.is_valid is False


def test_type_validator_flags_wrong_type() -> None:
    result = TypeValidator({"price": (int, float)}).validate(_record(price="cheap"))
    assert result.is_valid is False
    assert result.issues[0].code == "wrong-type"


def test_type_validator_ignores_absent() -> None:
    assert TypeValidator({"price": int}).validate(_record()).is_valid is True


def test_format_validator_checks_email() -> None:
    good = FormatValidator({"email": "email"}).validate(_record(email="a@b.co"))
    bad = FormatValidator({"email": "email"}).validate(_record(email="nope"))
    assert good.is_valid is True
    assert bad.is_valid is False


def test_format_validator_unknown_format_raises() -> None:
    try:
        FormatValidator({"x": "bogus"}).validate(_record(x="v"))
    except ValueError as exc:
        assert "unknown format" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_non_empty_validator() -> None:
    assert NonEmptyRecordValidator().validate(_record(name="X")).is_valid is True
    assert NonEmptyRecordValidator().validate(_record(name="")).is_valid is False


def test_collection_validator_bounds() -> None:
    validator = CollectionValidator("tags", min_items=1, max_items=2)
    assert validator.validate(_record(tags=["a"])).is_valid is True
    too_few = validator.validate(_record(tags=[]))
    assert too_few.is_valid is False


def test_collection_validator_rejects_non_collection() -> None:
    result = CollectionValidator("tags").validate(_record(tags="notalist"))
    assert result.issues[0].code == "not-a-collection"


def test_nested_validator_checks_keys() -> None:
    validator = NestedObjectValidator("address", ["city", "postcode"])
    ok = validator.validate(_record(address={"city": "London", "postcode": "SW1"}))
    missing = validator.validate(_record(address={"city": "London"}))
    assert ok.is_valid is True
    assert missing.is_valid is False


def test_nested_validator_rejects_non_object() -> None:
    result = NestedObjectValidator("address", ["city"]).validate(_record(address="text"))
    assert result.issues[0].code == "not-an-object"


def test_format_validator_skips_absent_field() -> None:
    # Field not present -> value is None -> validator skips it, remains valid.
    assert FormatValidator({"email": "email"}).validate(_record(name="X")).is_valid is True


def test_format_validator_accepts_compiled_pattern() -> None:
    import re

    pattern = re.compile(r"^\d{3}$")
    good = FormatValidator({"code": pattern}).validate(_record(code="123"))
    bad = FormatValidator({"code": pattern}).validate(_record(code="12"))
    assert good.is_valid is True
    assert bad.is_valid is False


def test_nested_validator_flags_missing_key_value() -> None:
    # Key present but its value is blank -> treated as missing.
    result = NestedObjectValidator("address", ["city"]).validate(_record(address={"city": "  "}))
    assert result.is_valid is False
    assert result.issues[0].code == "missing-nested-key"
