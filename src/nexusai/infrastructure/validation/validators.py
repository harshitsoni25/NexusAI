"""Structural validators.

Structural validation asks whether a record is well-formed: are the required
fields present, are they the right type, do collections and nested objects hold
together. Each validator implements the
:class:`~nexusai.domain.ports.validation.Validator` port over a
:class:`~nexusai.domain.model.processing.ProcessedRecord` and returns a
:class:`~nexusai.domain.model.assessment.ValidationResult` -- a *finding*, not
an exception, because a malformed record is data to be reported, not an error to
be raised.

A finding's severity classifies it: an ``ERROR`` or worse makes the record
invalid (a FAIL); a ``WARNING`` leaves it valid but noted; no issues is a clean
PASS.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from nexusai.domain.model.assessment import Severity, ValidationIssue, ValidationResult
from nexusai.domain.model.processing import ProcessedRecord
from nexusai.shared.types import JsonValue

_FORMATS: Mapping[str, re.Pattern[str]] = {
    "email": re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
    "url": re.compile(r"^https?://[^\s]+$"),
    "integer": re.compile(r"^-?\d+$"),
    "decimal": re.compile(r"^-?\d+(\.\d+)?$"),
    "iso-date": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
}


class RequiredFieldsValidator:
    """Fails a record that is missing any of its required fields.

    A field is considered missing if it is absent, ``None`` or an empty string,
    which is the common case a scraper must guard against.
    """

    name = "required-fields"

    def __init__(self, required: Sequence[str], *, severity: Severity = Severity.ERROR) -> None:
        self._required = tuple(required)
        self._severity = severity

    def validate(self, value: ProcessedRecord) -> ValidationResult:
        """Report a missing-field issue for each absent required field."""
        issues = [
            ValidationIssue(
                code="missing-required-field",
                message=f"required field {name!r} is missing",
                severity=self._severity,
                location=name,
            )
            for name in self._required
            if _is_missing(value.value(name))
        ]
        return ValidationResult(issues=issues, checked=len(self._required))


class TypeValidator:
    """Checks that named fields hold values of the expected Python types.

    Args:
        expected: A mapping of field name to a type or tuple of acceptable types.
    """

    name = "types"

    def __init__(self, expected: Mapping[str, type | tuple[type, ...]]) -> None:
        self._expected = dict(expected)

    def validate(self, value: ProcessedRecord) -> ValidationResult:
        """Report a type issue for each field of the wrong type."""
        issues: list[ValidationIssue] = []
        for name, types in self._expected.items():
            actual = value.value(name)
            if actual is not None and not isinstance(actual, types):
                issues.append(
                    ValidationIssue(
                        code="wrong-type",
                        message=f"field {name!r} has type {type(actual).__name__}",
                        severity=Severity.ERROR,
                        location=name,
                    )
                )
        return ValidationResult(issues=issues, checked=len(self._expected))


class FormatValidator:
    """Checks that named fields match a named format, such as ``email``.

    Args:
        fields: A mapping of field name to format name. Supported formats are
            ``email``, ``url``, ``integer``, ``decimal`` and ``iso-date``; a
            custom pattern can be supplied by passing a compiled regex as the
            value instead of a name.
    """

    name = "formats"

    def __init__(self, fields: Mapping[str, str | re.Pattern[str]]) -> None:
        self._fields = dict(fields)

    def validate(self, value: ProcessedRecord) -> ValidationResult:
        """Report a format issue for each field failing its pattern."""
        issues: list[ValidationIssue] = []
        for name, spec in self._fields.items():
            actual = value.value(name)
            if actual is None:
                continue
            pattern = spec if isinstance(spec, re.Pattern) else _FORMATS.get(spec)
            if pattern is None:
                raise ValueError(f"unknown format: {spec!r}")
            if not isinstance(actual, str) or not pattern.match(actual):
                issues.append(
                    ValidationIssue(
                        code="invalid-format",
                        message=f"field {name!r} does not match format",
                        severity=Severity.ERROR,
                        location=name,
                    )
                )
        return ValidationResult(issues=issues, checked=len(self._fields))


class NonEmptyRecordValidator:
    """Fails a record that has no populated fields at all.

    An empty record usually means extraction found nothing on the page, which is
    worth flagging distinctly from a record that is merely missing one field.
    """

    name = "non-empty"

    def validate(self, value: ProcessedRecord) -> ValidationResult:
        """Report an issue if the record holds no non-missing values."""
        if any(not _is_missing(field_value) for field_value in value.values().values()):
            return ValidationResult.passing()
        return ValidationResult(
            issues=[
                ValidationIssue(
                    code="empty-record",
                    message="record has no populated fields",
                    severity=Severity.ERROR,
                )
            ]
        )


class CollectionValidator:
    """Checks that a named collection field holds between min and max items.

    Args:
        field: The collection field to check.
        min_items: The minimum acceptable length.
        max_items: The maximum acceptable length, or ``None`` for no maximum.
    """

    name = "collection"

    def __init__(self, field: str, *, min_items: int = 0, max_items: int | None = None) -> None:
        self._field = field
        self._min = min_items
        self._max = max_items

    def validate(self, value: ProcessedRecord) -> ValidationResult:
        """Report an issue if the collection's length is out of bounds."""
        actual = value.value(self._field)
        if not isinstance(actual, Sequence) or isinstance(actual, str):
            return ValidationResult(
                issues=[
                    ValidationIssue(
                        code="not-a-collection",
                        message=f"field {self._field!r} is not a collection",
                        severity=Severity.ERROR,
                        location=self._field,
                    )
                ]
            )
        issues: list[ValidationIssue] = []
        if len(actual) < self._min:
            issues.append(
                ValidationIssue(
                    code="collection-too-small",
                    message=f"{self._field!r} has fewer than {self._min} items",
                    severity=Severity.ERROR,
                    location=self._field,
                )
            )
        if self._max is not None and len(actual) > self._max:
            issues.append(
                ValidationIssue(
                    code="collection-too-large",
                    message=f"{self._field!r} has more than {self._max} items",
                    severity=Severity.WARNING,
                    location=self._field,
                )
            )
        return ValidationResult(issues=issues, checked=1)


class NestedObjectValidator:
    """Checks that a named field holds a mapping with its own required keys.

    Args:
        field: The field expected to hold a nested object.
        required_keys: Keys the nested object must contain.
    """

    name = "nested"

    def __init__(self, field: str, required_keys: Sequence[str]) -> None:
        self._field = field
        self._keys = tuple(required_keys)

    def validate(self, value: ProcessedRecord) -> ValidationResult:
        """Report issues for a missing or incomplete nested object."""
        actual = value.value(self._field)
        if not isinstance(actual, Mapping):
            return ValidationResult(
                issues=[
                    ValidationIssue(
                        code="not-an-object",
                        message=f"field {self._field!r} is not a nested object",
                        severity=Severity.ERROR,
                        location=self._field,
                    )
                ]
            )
        issues = [
            ValidationIssue(
                code="missing-nested-key",
                message=f"nested object {self._field!r} is missing key {key!r}",
                severity=Severity.ERROR,
                location=f"{self._field}.{key}",
            )
            for key in self._keys
            if key not in actual or _is_missing(actual[key])
        ]
        return ValidationResult(issues=issues, checked=len(self._keys))


def _is_missing(value: JsonValue) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


__all__ = [
    "CollectionValidator",
    "FormatValidator",
    "NestedObjectValidator",
    "NonEmptyRecordValidator",
    "RequiredFieldsValidator",
    "TypeValidator",
]
