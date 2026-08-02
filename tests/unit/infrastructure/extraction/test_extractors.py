"""Tests for every extraction mechanism, run over the parser abstraction."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nexusai.domain.model.retrieval import Document
from nexusai.domain.ports.documents import ParsedDocument
from nexusai.infrastructure.extraction import (
    AttributeExtractor,
    CssExtractor,
    ImageExtractor,
    JsonPathExtractor,
    LinkExtractor,
    MetadataExtractor,
    RegexExtractor,
    TableExtractor,
    XPathExtractor,
)
from nexusai.infrastructure.parsing.markup import HtmlParser
from nexusai.infrastructure.parsing.structured import JsonParser, TextParser

PAGE = (
    b"<html><head><title>Shop</title>"
    b'<meta name="author" content="Team"><meta property="og:type" content="site"></head>'
    b'<body><h1 id="hd">Widgets</h1>'
    b'<a href="/a">Alpha</a><a href="/b">Beta</a>'
    b'<img src="/i.png" alt="pic">'
    b"<table><tr><th>Name</th><th>Qty</th></tr>"
    b"<tr><td>Bolt</td><td>10</td></tr><tr><td>Nut</td><td>20</td></tr></table>"
    b'<span data-sku="S1">x</span><span data-sku="S2">y</span></body></html>'
)


def _doc(content: bytes, media_type: str) -> Document:
    return Document(
        url="https://shop.example",
        content=content,
        status_code=200,
        provider="test",
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        media_type=media_type,
        encoding="utf-8",
    )


def _html() -> ParsedDocument:
    return HtmlParser().parse(_doc(PAGE, "text/html"))


def test_css_extracts_text_and_records_provenance() -> None:
    result = CssExtractor().extract(_html(), {"heading": "#hd"})
    field = result.fields["heading"]
    assert field.value == "Widgets"
    assert field.provenance.method.value == "css"
    assert field.provenance.dom_path == "/html/body/h1"


def test_css_reads_attribute_and_collects_many() -> None:
    result = CssExtractor().extract(
        _html(),
        {
            "first_href": {"selector": "a", "attribute": "href"},
            "all_links": {"selector": "a", "many": True},
        },
    )
    assert result.fields["first_href"].value == "/a"
    assert [item.value for item in result.collections["all_links"]] == ["Alpha", "Beta"]


def test_css_missing_selector_marks_not_found() -> None:
    result = CssExtractor().extract(_html(), {"nope": ".absent"})
    assert result.fields["nope"].found is False


def test_css_rejects_malformed_spec() -> None:
    with pytest.raises(ValueError, match="selector"):
        CssExtractor().extract(_html(), {"x": {"attribute": "href"}})
    with pytest.raises(TypeError):
        CssExtractor().extract(_html(), {"x": 123})


def test_xpath_extractor_reads_attribute_values() -> None:
    result = XPathExtractor().extract(_html(), {"first": "//a/@href"})
    assert result.fields["first"].value == "/a"


def test_regex_extracts_group_and_many() -> None:
    doc = TextParser().parse(_doc(b"id=42 id=99 id=7", "text/plain"))
    single = RegexExtractor().extract(doc, {"first": r"id=(\d+)"})
    assert single.fields["first"].value == "42"
    many = RegexExtractor().extract(doc, {"all": {"pattern": r"id=(\d+)", "many": True}})
    assert [item.value for item in many.collections["all"]] == ["42", "99", "7"]


def test_regex_missing_marks_not_found_and_validates_pattern() -> None:
    doc = TextParser().parse(_doc(b"nothing", "text/plain"))
    assert RegexExtractor().extract(doc, {"x": r"(\d+)"}).fields["x"].found is False
    with pytest.raises(ValueError, match="invalid regular expression"):
        RegexExtractor().extract(doc, {"x": "("})


def test_json_path_resolves_nested_and_indexed_paths() -> None:
    doc = JsonParser().parse(
        _doc(b'{"result": {"items": [{"name": "n1"}, {"name": "n2"}]}}', "application/json")
    )
    result = JsonPathExtractor().extract(
        doc, {"first": "result.items[0].name", "second": "$.result.items[1].name"}
    )
    assert result.fields["first"].value == "n1"
    assert result.fields["second"].value == "n2"


def test_json_path_handles_absent_and_out_of_range() -> None:
    doc = JsonParser().parse(_doc(b'{"a": [1]}', "application/json"))
    result = JsonPathExtractor().extract(doc, {"x": "a[5]", "y": "b.c"})
    assert result.fields["x"].found is False
    assert result.fields["y"].found is False
    with pytest.raises(TypeError):
        JsonPathExtractor().extract(doc, {"z": 5})


def test_table_extractor_reads_rows_as_header_mappings() -> None:
    result = TableExtractor().extract(_html(), {"rows": "table"})
    rows = [item.value for item in result.collections["rows"]]
    assert rows == [{"Name": "Bolt", "Qty": "10"}, {"Name": "Nut", "Qty": "20"}]


def test_table_extractor_without_header_returns_cell_lists() -> None:
    result = TableExtractor().extract(_html(), {"rows": {"selector": "table", "header": False}})
    rows = [item.value for item in result.collections["rows"]]
    assert rows[0] == ["Name", "Qty"]


def test_metadata_extractor_reads_title_and_meta() -> None:
    result = MetadataExtractor().extract(_html(), {})
    meta = result.fields["metadata"].value
    assert meta == {"title": "Shop", "author": "Team", "og:type": "site"}


def test_link_extractor_resolves_relative_urls() -> None:
    result = LinkExtractor().extract(_html(), {"base": "https://shop.example/"})
    links = [item.value for item in result.collections["links"]]
    assert links[0] == {"url": "https://shop.example/a", "text": "Alpha"}


def test_image_extractor_resolves_and_defaults_alt() -> None:
    result = ImageExtractor().extract(_html(), {"base": "https://shop.example/"})
    images = [item.value for item in result.collections["images"]]
    assert images == [{"src": "https://shop.example/i.png", "alt": "pic"}]


def test_attribute_extractor_collects_all_matches() -> None:
    result = AttributeExtractor().extract(
        _html(), {"skus": {"selector": "span", "attribute": "data-sku"}}
    )
    assert [item.value for item in result.collections["skus"]] == ["S1", "S2"]


def test_attribute_extractor_validates_spec() -> None:
    with pytest.raises(TypeError):
        AttributeExtractor().extract(_html(), {"x": "not-a-mapping"})
    with pytest.raises(TypeError):
        AttributeExtractor().extract(_html(), {"x": {"selector": "span"}})


def test_regex_named_group_and_group_errors() -> None:
    doc = TextParser().parse(_doc(b"user=alice", "text/plain"))
    named = RegexExtractor().extract(doc, {"u": {"pattern": r"user=(?P<who>\w+)", "group": "who"}})
    assert named.fields["u"].value == "alice"
    with pytest.raises(ValueError, match="no such regex group"):
        RegexExtractor().extract(doc, {"u": {"pattern": r"user=(\w+)", "group": 9}})


def test_regex_whole_match_when_no_group() -> None:
    doc = TextParser().parse(_doc(b"abc123", "text/plain"))
    result = RegexExtractor().extract(doc, {"m": r"\d+"})
    assert result.fields["m"].value == "123"


def test_regex_spec_validation() -> None:
    doc = TextParser().parse(_doc(b"x", "text/plain"))
    with pytest.raises(ValueError, match="pattern"):
        RegexExtractor().extract(doc, {"x": {"group": 1}})
    with pytest.raises(ValueError, match="group"):
        RegexExtractor().extract(doc, {"x": {"pattern": "a", "group": 1.5}})
    with pytest.raises(TypeError):
        RegexExtractor().extract(doc, {"x": 123})


def test_json_path_stops_descending_into_scalars() -> None:
    doc = JsonParser().parse(_doc(b'{"a": "text"}', "application/json"))
    # 'a' is a string; indexing into it must report not-found rather than error.
    result = JsonPathExtractor().extract(doc, {"x": "a.b", "y": "a[0]"})
    assert result.fields["x"].found is False
    assert result.fields["y"].found is False


def test_table_without_rows_returns_empty_collection() -> None:
    parsed = HtmlParser().parse(_doc(b"<html><body><table></table></body></html>", "text/html"))
    result = TableExtractor().extract(parsed, {"rows": "table"})
    assert result.collections["rows"] == ()


def test_link_and_image_skip_elements_missing_url() -> None:
    parsed = HtmlParser().parse(_doc(b"<html><body><a>no href</a><img></body></html>", "text/html"))
    assert LinkExtractor().extract(parsed, {}).collections["links"] == ()
    assert ImageExtractor().extract(parsed, {}).collections["images"] == ()


def test_metadata_ignores_meta_without_content() -> None:
    parsed = HtmlParser().parse(
        _doc(b'<html><head><meta name="x"></head><body></body></html>', "text/html")
    )
    assert MetadataExtractor().extract(parsed, {}).fields["metadata"].value == {}
