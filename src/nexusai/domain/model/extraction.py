"""Models for extracted values and their provenance.

Extraction turns a parsed document into structured values, and every value
carries the trace of how it was obtained: which method, which selector, which
DOM path. That trace is the point -- a downstream reviewer, or a future change
detector, must be able to ask "where did this field come from?" and get an
answer richer than "the page".

These are generic containers. They describe the *shape* of an extraction result,
not the rules that populate it; those live with the extractors.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from nexusai.shared.types import JsonMapping, JsonValue


class ExtractionMethod(Enum):
    """How a value was extracted, recorded on its provenance."""

    CSS = "css"
    XPATH = "xpath"
    REGEX = "regex"
    JSON_PATH = "json_path"
    TABLE = "table"
    METADATA = "metadata"
    LINKS = "links"
    IMAGES = "images"
    ATTRIBUTE = "attribute"
    TEXT = "text"
    NESTED = "nested"


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldProvenance:
    """The trace of how a single value was extracted.

    Attributes:
        method: The extraction mechanism used.
        selector: The selector or pattern applied, where one applies.
        dom_path: The path to the matched node in the document, when the parser
            can supply one.
        parser: The name of the parser that produced the tree.
    """

    method: ExtractionMethod
    selector: str | None = None
    dom_path: str | None = None
    parser: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "method": self.method.value,
            "selector": self.selector,
            "dom_path": self.dom_path,
            "parser": self.parser,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtractedValue:
    """A single extracted value paired with its provenance.

    Attributes:
        value: The extracted data, as a JSON-safe value. A scalar for a single
            match, a list for a collection, a mapping for a nested object.
        provenance: How the value was obtained.
        found: Whether anything matched. A value of ``None`` with ``found`` false
            distinguishes "matched nothing" from "matched an empty string".
    """

    value: JsonValue
    provenance: FieldProvenance
    found: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "value": self.value,
            "found": self.found,
            "provenance": self.provenance.to_dict(),
        }

    @classmethod
    def missing(cls, provenance: FieldProvenance) -> ExtractedValue:
        """Return a value representing "nothing matched"."""
        return cls(value=None, provenance=provenance, found=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtractionResult:
    """A named collection of extracted values from one document.

    The unit an extraction pass returns: the fields it pulled, keyed by name,
    each with its own provenance, plus document-level metadata. It carries no
    judgement about whether the values are *correct* or *complete* -- that is
    validation and quality, which are later phases operating on this output.
    """

    fields: Mapping[str, ExtractedValue] = field(default_factory=dict)
    collections: Mapping[str, Sequence[ExtractedValue]] = field(default_factory=dict)
    metadata: JsonMapping = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", dict(self.fields))
        object.__setattr__(
            self, "collections", {key: tuple(items) for key, items in self.collections.items()}
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

    def value(self, name: str) -> JsonValue:
        """Return the plain value of field ``name``, or ``None`` if absent."""
        field_value = self.fields.get(name)
        return field_value.value if field_value is not None else None

    def with_field(self, name: str, value: ExtractedValue) -> ExtractionResult:
        """Return a copy with an additional field."""
        return ExtractionResult(
            fields={**self.fields, name: value},
            collections=self.collections,
            metadata=self.metadata,
        )

    def merge(self, other: ExtractionResult) -> ExtractionResult:
        """Return a copy combining this result with ``other``.

        Later fields win on key collision, which lets a specific extractor
        override a general one when both are run.
        """
        return ExtractionResult(
            fields={**self.fields, **other.fields},
            collections={**self.collections, **other.collections},
            metadata={**self.metadata, **other.metadata},
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "fields": {name: value.to_dict() for name, value in self.fields.items()},
            "collections": {
                name: [item.to_dict() for item in items] for name, items in self.collections.items()
            },
            "metadata": dict(self.metadata),
        }
