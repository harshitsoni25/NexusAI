"""Extractors that read text and structured data rather than a markup tree.

The regular-expression extractor runs against the document's text view, so it
works on any format, markup or not. The JSON-path extractor walks the decoded
data view with a small dotted-and-bracketed path grammar, avoiding a third-party
path dependency for needs this modest.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from nexusai.domain.model.extraction import (
    ExtractedValue,
    ExtractionMethod,
    ExtractionResult,
    FieldProvenance,
)
from nexusai.domain.ports.documents import ParsedDocument
from nexusai.shared.types import JsonValue


class RegexExtractor:
    """Extracts values by regular expression from the document text.

    A spec maps a field to a pattern string, or to a mapping with ``pattern``, an
    optional ``group`` (name or index, defaulting to the first group or the whole
    match), and ``many`` to collect every match rather than the first.
    """

    name = "regex"

    def extract(self, parsed: ParsedDocument, spec: Mapping[str, object]) -> ExtractionResult:
        """Extract fields from the document text per ``spec``."""
        text = _as_text(parsed.data())
        fields: dict[str, ExtractedValue] = {}
        collections: dict[str, Sequence[ExtractedValue]] = {}
        for name, raw in spec.items():
            pattern, group, many = _normalise_pattern(raw)
            compiled = _compile(pattern)
            provenance = FieldProvenance(method=ExtractionMethod.REGEX, selector=pattern)
            if many:
                collections[name] = tuple(
                    ExtractedValue(value=_group(match, group), provenance=provenance)
                    for match in compiled.finditer(text)
                )
                continue
            match = compiled.search(text)
            if match is None:
                fields[name] = ExtractedValue.missing(provenance)
            else:
                fields[name] = ExtractedValue(value=_group(match, group), provenance=provenance)
        return ExtractionResult(fields=fields, collections=collections)


class JsonPathExtractor:
    """Extracts values from decoded JSON data by a small path grammar.

    Paths are dotted for mapping keys and bracketed for sequence indices:
    ``result.items[0].name``. A leading ``$`` is accepted and ignored. The
    grammar is deliberately minimal -- no wildcards or filters -- because the
    framework's own needs are addressing, not querying; a plugin can supply a
    richer extractor where a site demands one.
    """

    name = "json_path"

    def extract(self, parsed: ParsedDocument, spec: Mapping[str, object]) -> ExtractionResult:
        """Extract fields from decoded data per ``spec`` of field to path."""
        data = parsed.data()
        fields: dict[str, ExtractedValue] = {}
        for name, raw in spec.items():
            if not isinstance(raw, str):
                raise TypeError(f"json_path spec for {name!r} must be a string path")
            provenance = FieldProvenance(method=ExtractionMethod.JSON_PATH, selector=raw)
            found, value = _resolve_path(data, raw)
            fields[name] = (
                ExtractedValue(value=value, provenance=provenance)
                if found
                else ExtractedValue.missing(provenance)
            )
        return ExtractionResult(fields=fields)


def _as_text(data: JsonValue) -> str:
    return data if isinstance(data, str) else str(data)


def _compile(pattern: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern, re.DOTALL)
    except re.error as exc:
        raise ValueError(f"invalid regular expression {pattern!r}: {exc}") from exc


def _group(match: re.Match[str], group: str | int | None) -> JsonValue:
    if group is None:
        return match.group(1) if match.groups() else match.group(0)
    try:
        return match.group(group)
    except (IndexError, re.error) as exc:
        raise ValueError(f"no such regex group: {group!r}") from exc


def _normalise_pattern(raw: object) -> tuple[str, str | int | None, bool]:
    if isinstance(raw, str):
        return raw, None, False
    if isinstance(raw, Mapping):
        pattern = raw.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            raise ValueError("a regex spec must include a non-empty 'pattern'")
        group = raw.get("group")
        if group is not None and not isinstance(group, (str, int)):
            raise ValueError("'group' must be a string or integer when provided")
        return pattern, group, bool(raw.get("many", False))
    raise TypeError(f"unsupported regex spec: {type(raw).__name__}")


def _resolve_path(data: JsonValue, path: str) -> tuple[bool, JsonValue]:
    """Resolve a dotted/bracketed path, returning (found, value)."""
    current: JsonValue = data
    for token in _tokenise(path):
        if isinstance(token, int):
            if not isinstance(current, Sequence) or isinstance(current, str):
                return False, None
            if not -len(current) <= token < len(current):
                return False, None
            current = current[token]
        elif isinstance(current, Mapping) and token in current:
            current = current[token]
        else:
            return False, None
    return True, current


def _tokenise(path: str) -> Sequence[str | int]:
    """Split a path into string keys and integer indices."""
    cleaned = path[1:] if path.startswith("$") else path
    tokens: list[str | int] = []
    for part in cleaned.replace("]", "").split("."):
        if not part:
            continue
        if "[" in part:
            key, _, index = part.partition("[")
            if key:
                tokens.append(key)
            tokens.append(int(index))
        else:
            tokens.append(part)
    return tokens
