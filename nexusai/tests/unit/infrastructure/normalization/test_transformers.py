"""Tests for the value transformers."""

from __future__ import annotations

import pytest

from nexusai.domain.errors.exceptions import TransformationError
from nexusai.infrastructure.normalization.transformers import (
    CaseTransformer,
    DateNormalizer,
    EnumMapper,
    NumericNormalizer,
    TypeConverter,
    UnicodeNormalizer,
    UrlNormalizer,
    WhitespaceCleaner,
)


def test_whitespace_collapses_and_trims() -> None:
    assert WhitespaceCleaner().transform("  a   b\tc  ") == "a b c"


def test_whitespace_passes_non_strings() -> None:
    assert WhitespaceCleaner().transform(42) == 42


def test_unicode_composes_by_default() -> None:
    assert UnicodeNormalizer().transform("e\u0301") == "\u00e9"


def test_unicode_rejects_unknown_form() -> None:
    with pytest.raises(ValueError, match="normalisation form"):
        UnicodeNormalizer(form="XYZ")


@pytest.mark.parametrize(
    ("case", "expected"),
    [("lower", "hello world"), ("upper", "HELLO WORLD"), ("title", "Hello World")],
)
def test_case_transformer(case: str, expected: str) -> None:
    assert CaseTransformer(case=case).transform("hello world") == expected


def test_numeric_strips_separators() -> None:
    assert NumericNormalizer().transform("$1,299.50") == 1299.5
    assert NumericNormalizer().transform("42") == 42
    assert isinstance(NumericNormalizer().transform("42"), int)


def test_numeric_passes_numbers_through() -> None:
    assert NumericNormalizer().transform(3.14) == 3.14


def test_numeric_lenient_passes_unparseable() -> None:
    assert NumericNormalizer().transform("n/a") == "n/a"


def test_numeric_strict_raises() -> None:
    with pytest.raises(TransformationError):
        NumericNormalizer(strict=True).transform("n/a")


def test_type_converter_bool() -> None:
    convert = TypeConverter(target="bool")
    assert convert.transform("yes") is True
    assert convert.transform("0") is False


def test_type_converter_int_from_float_string() -> None:
    assert TypeConverter(target="int").transform("42.0") == 42


def test_type_converter_strict_raises_on_bad_bool() -> None:
    with pytest.raises(TransformationError):
        TypeConverter(target="bool", strict=True).transform("maybe")


def test_date_normaliser_parses_formats() -> None:
    assert DateNormalizer().transform("25/12/2026") == "2026-12-25"
    assert DateNormalizer().transform("2026-01-05") == "2026-01-05"


def test_date_normaliser_with_time() -> None:
    result = DateNormalizer(with_time=True).transform("2026-01-05")
    assert isinstance(result, str) and result.startswith("2026-01-05T")


def test_date_normaliser_lenient_on_unknown() -> None:
    assert DateNormalizer().transform("not a date") == "not a date"


def test_url_normaliser_canonicalises() -> None:
    assert UrlNormalizer().transform("HTTPS://Example.COM:443/Path") == "https://example.com/Path"


def test_url_normaliser_resolves_relative() -> None:
    result = UrlNormalizer(base="https://example.com/a/").transform("../b")
    assert result == "https://example.com/b"


def test_enum_mapper_is_case_insensitive() -> None:
    mapper = EnumMapper({"GB": "United Kingdom"})
    assert mapper.transform("gb") == "United Kingdom"


def test_enum_mapper_default_and_passthrough() -> None:
    assert EnumMapper({"a": "A"}, default="unknown").transform("z") == "unknown"
    assert EnumMapper({"a": "A"}).transform("z") == "z"
