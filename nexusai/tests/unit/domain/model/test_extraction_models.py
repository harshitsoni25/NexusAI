"""Tests for the extraction result models."""

from __future__ import annotations

from nexusai.domain.model.extraction import (
    ExtractedValue,
    ExtractionMethod,
    ExtractionResult,
    FieldProvenance,
)


def _value(value: object, method: ExtractionMethod = ExtractionMethod.CSS) -> ExtractedValue:
    return ExtractedValue(value=value, provenance=FieldProvenance(method=method))  # type: ignore[arg-type]


def test_missing_value_reports_not_found() -> None:
    missing = ExtractedValue.missing(FieldProvenance(method=ExtractionMethod.CSS))
    assert missing.found is False
    assert missing.value is None


def test_result_value_returns_none_for_absent_field() -> None:
    result = ExtractionResult(fields={"a": _value("x")})
    assert result.value("a") == "x"
    assert result.value("missing") is None


def test_result_merge_lets_later_fields_win() -> None:
    first = ExtractionResult(fields={"a": _value("1"), "b": _value("2")})
    second = ExtractionResult(fields={"b": _value("override")})
    merged = first.merge(second)
    assert merged.value("a") == "1"
    assert merged.value("b") == "override"


def test_result_with_field_is_immutable() -> None:
    result = ExtractionResult(fields={"a": _value("1")})
    extended = result.with_field("b", _value("2"))
    assert "b" not in result.fields
    assert extended.value("b") == "2"


def test_collections_are_tupleised() -> None:
    result = ExtractionResult(collections={"items": [_value("1"), _value("2")]})
    assert isinstance(result.collections["items"], tuple)


def test_to_dict_round_trips_structure() -> None:
    result = ExtractionResult(
        fields={"a": _value("1")},
        collections={"items": [_value("x")]},
        metadata={"n": 1},
    )
    payload = result.to_dict()
    assert payload["fields"]["a"]["value"] == "1"
    assert payload["collections"]["items"][0]["value"] == "x"
    assert payload["metadata"] == {"n": 1}
