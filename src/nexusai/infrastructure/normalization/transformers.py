"""Concrete, deterministic value transformers.

Each transformer performs one named conversion and implements the
:class:`~nexusai.domain.ports.processing.Transformer` port. They are pure --
no clock, no network, no state -- so a transformation chain is fully replayable,
which is what makes processing testable and auditable.

The default posture is lenient: a transformer that cannot convert a value returns
it unchanged rather than raising, so one odd value never aborts a record. A
transformer constructed with ``strict=True`` raises
:class:`~nexusai.domain.errors.exceptions.TransformationError` instead, for
pipelines that would rather fail loudly.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from datetime import datetime
from typing import Literal, cast
from urllib.parse import urlsplit, urlunsplit

from nexusai.domain.errors.exceptions import TransformationError
from nexusai.shared.types import JsonValue

_WHITESPACE = re.compile(r"\s+")


def _fail_or_passthrough(name: str, value: JsonValue, strict: bool, detail: str) -> JsonValue:
    if strict:
        raise TransformationError(f"{name} could not transform value", detail=detail)
    return value


class WhitespaceCleaner:
    """Collapses runs of whitespace and trims the ends of a string."""

    name = "whitespace"

    def transform(self, value: JsonValue) -> JsonValue:
        """Collapse internal whitespace and strip a string value."""
        if not isinstance(value, str):
            return value
        return _WHITESPACE.sub(" ", value).strip()


class UnicodeNormalizer:
    """Applies a Unicode normalisation form to a string.

    Args:
        form: The normalisation form, one of ``NFC``, ``NFD``, ``NFKC``, ``NFKD``.
            ``NFC`` is the default: it composes characters so that visually
            identical strings compare equal.
    """

    name = "unicode"

    def __init__(self, *, form: str = "NFC") -> None:
        if form not in {"NFC", "NFD", "NFKC", "NFKD"}:
            raise ValueError(f"unknown normalisation form: {form}")
        self._form = cast(Literal["NFC", "NFD", "NFKC", "NFKD"], form)

    def transform(self, value: JsonValue) -> JsonValue:
        """Normalise a string value to the configured form."""
        if not isinstance(value, str):
            return value
        return unicodedata.normalize(self._form, value)


class CaseTransformer:
    """Standardises the case of a string.

    Args:
        case: ``lower``, ``upper`` or ``title``.
    """

    name = "case"

    def __init__(self, *, case: str = "lower") -> None:
        if case not in {"lower", "upper", "title"}:
            raise ValueError(f"unknown case: {case}")
        self._case = case

    def transform(self, value: JsonValue) -> JsonValue:
        """Recase a string value."""
        if not isinstance(value, str):
            return value
        if self._case == "lower":
            return value.lower()
        if self._case == "upper":
            return value.upper()
        return value.title()


class NumericNormalizer:
    """Parses a numeric string into an ``int`` or ``float``.

    Strips grouping separators and currency symbols, then converts. An integral
    value becomes an ``int``; a fractional one a ``float``.

    Args:
        strict: Raise on an unparseable value rather than passing it through.
    """

    name = "numeric"

    def __init__(self, *, strict: bool = False) -> None:
        self._strict = strict

    def transform(self, value: JsonValue) -> JsonValue:
        """Convert a numeric string to a number."""
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        if not isinstance(value, str):
            return _fail_or_passthrough(self.name, value, self._strict, "not a string")
        cleaned = re.sub(r"[^\d.\-+]", "", value.strip())
        if not cleaned or cleaned in {"-", "+", "."}:
            return _fail_or_passthrough(self.name, value, self._strict, "no digits")
        try:
            number = float(cleaned)
        except ValueError:
            return _fail_or_passthrough(self.name, value, self._strict, "unparseable")
        return int(number) if number.is_integer() else number


class TypeConverter:
    """Converts a value to a target scalar type.

    Args:
        target: ``str``, ``int``, ``float`` or ``bool``.
        strict: Raise on a failed conversion rather than passing the value
            through.
    """

    name = "type"
    _booleans_true = frozenset({"true", "yes", "1", "on"})
    _booleans_false = frozenset({"false", "no", "0", "off", ""})

    def __init__(self, *, target: str = "str", strict: bool = False) -> None:
        if target not in {"str", "int", "float", "bool"}:
            raise ValueError(f"unknown target type: {target}")
        self._target = target
        self._strict = strict

    def transform(self, value: JsonValue) -> JsonValue:
        """Convert ``value`` to the configured target type."""
        try:
            return self._convert(value)
        except (ValueError, TypeError) as exc:
            return _fail_or_passthrough(self.name, value, self._strict, str(exc))

    def _convert(self, value: JsonValue) -> JsonValue:
        if self._target == "str":
            return value if value is None else str(value)
        if self._target == "int":
            return int(float(value)) if isinstance(value, str) else int(value)  # type: ignore[arg-type]
        if self._target == "float":
            return float(value)  # type: ignore[arg-type]
        return self._to_bool(value)

    def _to_bool(self, value: JsonValue) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in self._booleans_true:
                return True
            if lowered in self._booleans_false:
                return False
            raise ValueError(f"not a boolean: {value!r}")
        return bool(value)


class DateNormalizer:
    """Parses a date string into an ISO-8601 date or datetime string.

    Args:
        input_formats: The ``strptime`` formats to try, in order.
        with_time: Emit a full ISO datetime rather than a date.
        strict: Raise on an unparseable value rather than passing it through.
    """

    name = "date"

    def __init__(
        self,
        *,
        input_formats: tuple[str, ...] = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d %b %Y"),
        with_time: bool = False,
        strict: bool = False,
    ) -> None:
        self._formats = input_formats
        self._with_time = with_time
        self._strict = strict

    def transform(self, value: JsonValue) -> JsonValue:
        """Parse and re-emit a date string in ISO-8601 form."""
        if not isinstance(value, str):
            return _fail_or_passthrough(self.name, value, self._strict, "not a string")
        for fmt in self._formats:
            try:
                parsed = datetime.strptime(value.strip(), fmt)
            except ValueError:
                continue
            return parsed.isoformat() if self._with_time else parsed.date().isoformat()
        return _fail_or_passthrough(self.name, value, self._strict, "no format matched")


class UrlNormalizer:
    """Canonicalises a URL: lower-cased scheme and host, no default port.

    Args:
        base: A base URL to resolve a relative reference against, when given.
    """

    name = "url"

    def __init__(self, *, base: str = "") -> None:
        self._base = base

    def transform(self, value: JsonValue) -> JsonValue:
        """Return a canonical form of a URL string."""
        if not isinstance(value, str) or not value.strip():
            return value
        candidate = value.strip()
        if self._base:
            from urllib.parse import urljoin

            candidate = urljoin(self._base, candidate)
        parts = urlsplit(candidate)
        netloc = parts.hostname or ""
        if parts.port and not _is_default_port(parts.scheme, parts.port):
            netloc = f"{netloc}:{parts.port}"
        path = parts.path or "/"
        return urlunsplit((parts.scheme.lower(), netloc.lower(), path, parts.query, ""))


class EnumMapper:
    """Maps a raw value onto a canonical value via a lookup table.

    Args:
        mapping: Raw-to-canonical pairs. Lookup is case-insensitive for strings.
        default: The value to emit for an unmapped input; ``None`` passes the
            original through.
    """

    name = "enum"

    def __init__(self, mapping: Mapping[str, JsonValue], *, default: JsonValue = None) -> None:
        self._mapping = {key.lower(): val for key, val in mapping.items()}
        self._default = default
        self._has_default = default is not None

    def transform(self, value: JsonValue) -> JsonValue:
        """Map ``value`` onto its canonical form."""
        if not isinstance(value, str):
            return value
        mapped = self._mapping.get(value.strip().lower())
        if mapped is not None:
            return mapped
        return self._default if self._has_default else value


def _is_default_port(scheme: str, port: int) -> bool:
    return (scheme, port) in {("http", 80), ("https", 443), ("ftp", 21)}


__all__ = [
    "CaseTransformer",
    "DateNormalizer",
    "EnumMapper",
    "NumericNormalizer",
    "TypeConverter",
    "UnicodeNormalizer",
    "UrlNormalizer",
    "WhitespaceCleaner",
]
