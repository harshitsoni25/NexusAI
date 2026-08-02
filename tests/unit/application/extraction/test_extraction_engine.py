"""Tests for the extraction engine: parser selection and extractor merge."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nexusai.application.extraction import ExtractionEngine, ExtractionSpec
from nexusai.domain.errors.exceptions import DocumentParseError, ExtractionError
from nexusai.domain.model.retrieval import Document
from nexusai.domain.ports.documents import Extractor, Parser
from nexusai.infrastructure.extraction import (
    CssExtractor,
    LinkExtractor,
    RegexExtractor,
)
from nexusai.infrastructure.parsing.markup import HtmlParser, XmlParser
from nexusai.infrastructure.parsing.structured import JsonParser, TextParser
from nexusai.shared.registry import Registry


def _engine() -> ExtractionEngine:
    parsers: Registry[Parser] = Registry("parser")
    for parser in (HtmlParser(), XmlParser(), JsonParser(), TextParser()):
        parsers.register(parser.name, parser)
    extractors: Registry[Extractor] = Registry("extractor")
    for extractor in (CssExtractor(), LinkExtractor(), RegexExtractor()):
        extractors.register(extractor.name, extractor)
    return ExtractionEngine(parsers, extractors)


def _doc(content: bytes, media_type: str, url: str = "https://x/") -> Document:
    return Document(
        url=url,
        content=content,
        status_code=200,
        provider="http",
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        media_type=media_type,
        encoding="utf-8",
    )


def test_engine_selects_parser_by_media_type() -> None:
    parsed = _engine().parse(_doc(b'{"a": 1}', "application/json"))
    assert parsed.parser == "json"


def test_engine_forces_named_parser() -> None:
    parsed = _engine().parse(_doc(b"plain", "application/json"), parser_name="text")
    assert parsed.parser == "text"


def test_engine_falls_back_to_text_for_unknown_type() -> None:
    parsed = _engine().parse(_doc(b"body", "application/x-unknown"))
    assert parsed.parser == "text"


def test_engine_extracts_and_merges_and_stamps_parser() -> None:
    document = _doc(b'<html><body><h1>Hi</h1><a href="/p">P</a></body></html>', "text/html")
    spec = ExtractionSpec(extractors={"css": {"heading": "h1"}, "links": {"base": "https://x/"}})
    result = _engine().extract(document, spec)
    assert result.value("heading") == "Hi"
    assert result.fields["heading"].provenance.parser == "html"
    assert [item.value for item in result.collections["links"]] == [
        {"url": "https://x/p", "text": "P"}
    ]


def test_engine_rejects_unknown_extractor() -> None:
    with pytest.raises(ExtractionError, match="No such extractor"):
        _engine().extract(
            _doc(b"<html></html>", "text/html"), ExtractionSpec(extractors={"nope": {}})
        )


def test_engine_rejects_unknown_parser_name() -> None:
    with pytest.raises(DocumentParseError, match="No such parser"):
        _engine().parse(_doc(b"x", "text/html"), parser_name="missing")


def test_engine_without_fallback_raises_for_unknown_type() -> None:
    parsers: Registry[Parser] = Registry("parser")
    parsers.register("html", HtmlParser())
    engine = ExtractionEngine(parsers, Registry("extractor"), fallback_parser="text")
    with pytest.raises(DocumentParseError, match="no fallback"):
        engine.parse(_doc(b"x", "application/x-unknown"))
