"""The extraction engine.

Given a document and a specification, the engine parses the document with the
parser registered for its media type, then runs each named extractor over the
parsed tree with that extractor's slice of the spec, merging the results into one
:class:`ExtractionResult`. Selecting the parser by MIME type -- rather than the
caller naming it -- is what lets one extraction spec run unchanged over an HTML
page and its JSON API equivalent, provided the selectors suit each.

The engine holds registries of parsers and extractors, so a plugin adds a parser
or an extractor by registering it; the engine's own code never changes to gain a
new format or mechanism.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from nexusai.domain.errors.exceptions import DocumentParseError, ExtractionError
from nexusai.domain.model.extraction import (
    ExtractedValue,
    ExtractionResult,
    FieldProvenance,
)
from nexusai.domain.model.retrieval import Document
from nexusai.domain.ports.documents import Extractor, ParsedDocument, Parser
from nexusai.shared.registry import Registry


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtractionSpec:
    """A declarative extraction plan.

    Attributes:
        extractors: A mapping from extractor name to that extractor's spec -- the
            field-to-selector map it interprets. The engine runs each named
            extractor with its slice and merges the results.
        parser: An optional parser name forcing a specific parser, overriding
            selection by media type for documents whose type is mislabelled.
    """

    extractors: Mapping[str, Mapping[str, object]] = field(default_factory=dict)
    parser: str | None = None


class ExtractionEngine:
    """Coordinates parsing and extraction over a document."""

    def __init__(
        self,
        parsers: Registry[Parser],
        extractors: Registry[Extractor],
        *,
        fallback_parser: str = "text",
    ) -> None:
        self._parsers = parsers
        self._extractors = extractors
        self._fallback = fallback_parser
        self._by_media_type = _index_by_media_type(parsers)

    def parse(self, document: Document, *, parser_name: str | None = None) -> ParsedDocument:
        """Parse ``document`` with the named parser, or one chosen by media type.

        Raises:
            DocumentParseError: If no parser handles the document and no fallback
                is registered, or if parsing fails.
        """
        parser = self._resolve_parser(document, parser_name)
        return parser.parse(document)

    def extract(self, document: Document, spec: ExtractionSpec) -> ExtractionResult:
        """Parse ``document`` and run ``spec``'s extractors, merging results.

        Raises:
            DocumentParseError: If the document cannot be parsed.
            ExtractionError: If a named extractor is not registered.
        """
        parsed = self.parse(document, parser_name=spec.parser)
        result = ExtractionResult()
        for name, extractor_spec in spec.extractors.items():
            extractor = self._extractors.get_or_none(name)
            if extractor is None:
                raise ExtractionError("No such extractor", extractor=name)
            result = result.merge(extractor.extract(parsed, extractor_spec))
        return _stamp_parser(result, parsed.parser)

    def _resolve_parser(self, document: Document, parser_name: str | None) -> Parser:
        if parser_name is not None:
            parser = self._parsers.get_or_none(parser_name)
            if parser is None:
                raise DocumentParseError("No such parser", parser=parser_name)
            return parser
        chosen = self._by_media_type.get(document.media_type)
        if chosen is not None:
            return chosen
        fallback = self._parsers.get_or_none(self._fallback)
        if fallback is None:
            raise DocumentParseError(
                "No parser handles the document and no fallback is registered",
                media_type=document.media_type,
            )
        return fallback


def _stamp_parser(result: ExtractionResult, parser: str) -> ExtractionResult:
    """Record the parser name on every field's provenance that lacks one.

    Extractors do not know which parser produced their tree, so the engine fills
    it in afterwards; this is what makes "which parser was used?" answerable from
    any extracted value, satisfying the source-traceability requirement.
    """
    return ExtractionResult(
        fields={name: _with_parser(value, parser) for name, value in result.fields.items()},
        collections={
            name: tuple(_with_parser(item, parser) for item in items)
            for name, items in result.collections.items()
        },
        metadata=result.metadata,
    )


def _with_parser(value: ExtractedValue, parser: str) -> ExtractedValue:
    if value.provenance.parser is not None:
        return value
    stamped = FieldProvenance(
        method=value.provenance.method,
        selector=value.provenance.selector,
        dom_path=value.provenance.dom_path,
        parser=parser,
    )
    return ExtractedValue(value=value.value, provenance=stamped, found=value.found)


def _index_by_media_type(parsers: Registry[Parser]) -> Mapping[str, Parser]:
    """Build a media-type-to-parser index from the registry contents."""
    index: dict[str, Parser] = {}
    for name in parsers.names():
        parser = parsers.get(name)
        for media_type in parser.media_types:
            index.setdefault(media_type, parser)
    return index
