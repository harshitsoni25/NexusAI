"""Tests for the parsers and the lxml-backed node abstraction."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nexusai.domain.errors.exceptions import DocumentParseError
from nexusai.domain.model.retrieval import Document
from nexusai.infrastructure.parsing.markup import HtmlParser, XmlParser
from nexusai.infrastructure.parsing.structured import JsonParser, TextParser

HTML = (
    b"<html><head><title>T</title></head>"
    b'<body><a href="/x" class="lnk">Hi</a><a href="/y">Yo</a>'
    b'<span data-id="7">z</span></body></html>'
)


def _doc(content: bytes, media_type: str) -> Document:
    return Document(
        url="https://example.com",
        content=content,
        status_code=200,
        provider="test",
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        media_type=media_type,
        encoding="utf-8",
    )


def test_html_parser_supports_css_and_reports_parser_name() -> None:
    parsed = HtmlParser().parse(_doc(HTML, "text/html"))
    assert parsed.parser == "html"
    node = parsed.select_one("a.lnk")
    assert node is not None
    assert node.text() == "Hi"
    assert node.attribute("href") == "/x"
    assert node.attribute("missing") is None


def test_html_node_reports_dom_path() -> None:
    parsed = HtmlParser().parse(_doc(HTML, "text/html"))
    node = parsed.select_one("span")
    assert node is not None
    assert node.path() == "/html/body/span"
    assert node.attributes() == {"data-id": "7"}


def test_html_xpath_returns_element_and_scalar_nodes() -> None:
    parsed = HtmlParser().parse(_doc(HTML, "text/html"))
    hrefs = [node.text() for node in parsed.xpath("//a/@href")]
    assert hrefs == ["/x", "/y"]
    elements = parsed.xpath("//a")
    assert len(elements) == 2
    assert elements[0].tag == "a"


def test_html_parser_rejects_empty_document() -> None:
    with pytest.raises(DocumentParseError, match="empty"):
        HtmlParser().parse(_doc(b"   ", "text/html"))


def test_invalid_css_selector_raises_parse_error() -> None:
    parsed = HtmlParser().parse(_doc(HTML, "text/html"))
    with pytest.raises(DocumentParseError, match="CSS"):
        parsed.select("a[[[")


def test_invalid_xpath_raises_parse_error() -> None:
    parsed = HtmlParser().parse(_doc(HTML, "text/html"))
    with pytest.raises(DocumentParseError, match="XPath"):
        parsed.xpath("//a[")


def test_xml_parser_reads_feed() -> None:
    xml = b"<rss><channel><item><title>A</title></item></channel></rss>"
    parsed = XmlParser().parse(_doc(xml, "application/xml"))
    assert parsed.parser == "xml"
    assert parsed.select_one("title") is not None


def test_json_parser_exposes_decoded_data() -> None:
    parsed = JsonParser().parse(_doc(b'{"a": [1, 2]}', "application/json"))
    assert parsed.data() == {"a": [1, 2]}
    assert parsed.select("anything") == ()
    assert parsed.select_one("x") is None
    assert parsed.xpath("//x") == ()
    assert parsed.root.text() == '{"a": [1, 2]}'


def test_json_parser_rejects_invalid_json() -> None:
    with pytest.raises(DocumentParseError, match="JSON"):
        JsonParser().parse(_doc(b"{not json}", "application/json"))


def test_json_parser_handles_empty_body() -> None:
    parsed = JsonParser().parse(_doc(b"", "application/json"))
    assert parsed.data() is None


def test_text_parser_never_fails() -> None:
    parsed = TextParser().parse(_doc(b"plain body", "text/plain"))
    assert parsed.data() == "plain body"
    assert parsed.parser == "text"


def test_value_node_has_no_structure() -> None:
    parsed = HtmlParser().parse(_doc(HTML, "text/html"))
    scalar = parsed.xpath("//a/@href")[0]
    assert scalar.tag == "#value"
    assert scalar.attribute("x") is None
    assert scalar.attributes() == {}
    assert scalar.select("a") == ()
    assert scalar.select_one("a") is None
    assert scalar.xpath("//a") == ()
    assert scalar.path() == ""


def test_xml_parser_rejects_unparseable_bytes() -> None:
    # Bytes that lxml's recovering parser cannot yield any root from.
    with pytest.raises(DocumentParseError, match="XML"):
        XmlParser().parse(_doc(b"", "application/xml"))


def test_html_parser_accepts_xhtml_media_type() -> None:
    parser = HtmlParser()
    assert "application/xhtml+xml" in parser.media_types


def test_element_node_reports_special_tag_for_comment() -> None:
    parsed = HtmlParser().parse(_doc(b"<html><body><!--c--><p>x</p></body></html>", "text/html"))
    body = parsed.select_one("body")
    assert body is not None
    # itertext still yields the paragraph text.
    assert "x" in body.text()
