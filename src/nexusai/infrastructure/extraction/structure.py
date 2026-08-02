"""Structure-aware extractors: tables, metadata, links, images, attributes.

These cover the recurring shapes a scraper pulls from a page without a per-field
selector for each: every link, every image, the head metadata, an HTML table as
rows. Each reads only the parsed-document abstraction and records provenance, so
a table extracted here is as traceable as a single CSS field.

The link and image extractors resolve relative URLs against a supplied base, so a
downstream consumer receives absolute URLs regardless of how the page wrote them.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from urllib.parse import urljoin

from nexusai.domain.model.extraction import (
    ExtractedValue,
    ExtractionMethod,
    ExtractionResult,
    FieldProvenance,
)
from nexusai.domain.ports.documents import Node, ParsedDocument
from nexusai.shared.types import JsonValue


class TableExtractor:
    """Extracts HTML tables as lists of row objects.

    A spec maps a field name to a table selector (default ``table``) or to a
    mapping with ``selector`` and an optional ``header`` flag. When headers are
    used, each row becomes a mapping keyed by the header cells; otherwise a row
    is a list of cell texts. The whole set of matched tables is returned as a
    collection, so a page with several tables yields several row lists.
    """

    name = "table"

    def extract(self, parsed: ParsedDocument, spec: Mapping[str, object]) -> ExtractionResult:
        """Extract tables from ``parsed`` per ``spec``."""
        collections: dict[str, Sequence[ExtractedValue]] = {}
        for name, raw in spec.items():
            selector, use_header = _table_spec(raw)
            tables = parsed.select(selector)
            rows: list[ExtractedValue] = []
            for table in tables:
                provenance = FieldProvenance(
                    method=ExtractionMethod.TABLE, selector=selector, dom_path=table.path()
                )
                for row in _table_rows(table, use_header):
                    rows.append(ExtractedValue(value=row, provenance=provenance))
            collections[name] = tuple(rows)
        return ExtractionResult(collections=collections)


class MetadataExtractor:
    """Extracts document metadata: title and ``<meta>`` name/property values.

    Returns a single ``metadata`` field whose value is a mapping from meta name
    (or Open Graph property) to content, plus the document title. This is the
    head-level description a page advertises about itself, useful for provenance
    and downstream enrichment without a bespoke selector per tag.
    """

    name = "metadata"

    def extract(
        self,
        parsed: ParsedDocument,
        spec: Mapping[str, object],  # noqa: ARG002 - metadata takes no per-field spec
    ) -> ExtractionResult:
        """Extract head metadata; ``spec`` is accepted for contract parity."""
        meta: dict[str, JsonValue] = {}
        title = parsed.select_one("title")
        if title is not None:
            meta["title"] = title.text()
        for tag in parsed.select("meta"):
            key = tag.attribute("name") or tag.attribute("property")
            content = tag.attribute("content")
            if key and content is not None:
                meta[key] = content
        provenance = FieldProvenance(method=ExtractionMethod.METADATA, selector="head")
        return ExtractionResult(
            fields={"metadata": ExtractedValue(value=meta, provenance=provenance)}
        )


class LinkExtractor:
    """Extracts hyperlinks as absolute URLs with their link text.

    A spec may supply ``base`` (the document URL) to resolve relative hrefs and a
    ``selector`` (default ``a``). Each link becomes a mapping of ``url`` and
    ``text``; the set is returned as a ``links`` collection.
    """

    name = "links"

    def extract(self, parsed: ParsedDocument, spec: Mapping[str, object]) -> ExtractionResult:
        """Extract links from ``parsed`` per ``spec``."""
        base = _str(spec.get("base"), "")
        selector = _str(spec.get("selector"), "a")
        links: list[ExtractedValue] = []
        for node in parsed.select(selector):
            href = node.attribute("href")
            if href is None:
                continue
            provenance = FieldProvenance(
                method=ExtractionMethod.LINKS, selector=selector, dom_path=node.path()
            )
            value: JsonValue = {"url": _absolute(base, href), "text": node.text()}
            links.append(ExtractedValue(value=value, provenance=provenance))
        return ExtractionResult(collections={"links": tuple(links)})


class ImageExtractor:
    """Extracts images as absolute source URLs with their alt text.

    Mirrors :class:`LinkExtractor` for ``img`` elements: ``base`` resolves
    relative sources, and each image becomes a mapping of ``src`` and ``alt`` in
    an ``images`` collection.
    """

    name = "images"

    def extract(self, parsed: ParsedDocument, spec: Mapping[str, object]) -> ExtractionResult:
        """Extract images from ``parsed`` per ``spec``."""
        base = _str(spec.get("base"), "")
        selector = _str(spec.get("selector"), "img")
        images: list[ExtractedValue] = []
        for node in parsed.select(selector):
            src = node.attribute("src")
            if src is None:
                continue
            provenance = FieldProvenance(
                method=ExtractionMethod.IMAGES, selector=selector, dom_path=node.path()
            )
            value: JsonValue = {"src": _absolute(base, src), "alt": node.attribute("alt") or ""}
            images.append(ExtractedValue(value=value, provenance=provenance))
        return ExtractionResult(collections={"images": tuple(images)})


class AttributeExtractor:
    """Extracts a named attribute from every element matching a selector.

    A spec maps a field to a mapping with ``selector`` and ``attribute``. Where
    the selector-based extractors take the first match, this collects the named
    attribute across all matches, for pulling, say, every ``data-id`` on a page.
    """

    name = "attribute"

    def extract(self, parsed: ParsedDocument, spec: Mapping[str, object]) -> ExtractionResult:
        """Extract attributes from ``parsed`` per ``spec``."""
        collections: dict[str, Sequence[ExtractedValue]] = {}
        for name, raw in spec.items():
            if not isinstance(raw, Mapping):
                raise TypeError(f"attribute spec for {name!r} must be a mapping")
            selector = raw.get("selector")
            attribute = raw.get("attribute")
            if not isinstance(selector, str) or not isinstance(attribute, str):
                raise TypeError("attribute spec needs string 'selector' and 'attribute'")
            values: list[ExtractedValue] = []
            for node in parsed.select(selector):
                found = node.attribute(attribute)
                if found is None:
                    continue
                provenance = FieldProvenance(
                    method=ExtractionMethod.ATTRIBUTE,
                    selector=f"{selector}::attr({attribute})",
                    dom_path=node.path(),
                )
                values.append(ExtractedValue(value=found, provenance=provenance))
            collections[name] = tuple(values)
        return ExtractionResult(collections=collections)


def _table_rows(table: Node, use_header: bool) -> Sequence[JsonValue]:
    """Return a table's rows as header-keyed mappings or plain cell lists."""
    row_nodes = table.select("tr")
    rows: list[JsonValue] = []
    header: list[str] = []
    for index, row in enumerate(row_nodes):
        cells = [cell.text() for cell in row.select("th, td")]
        if use_header and index == 0:
            header = cells
            continue
        if use_header and header:
            rows.append(dict(zip(header, cells, strict=False)))
        else:
            rows.append(list(cells))
    return rows


def _table_spec(raw: object) -> tuple[str, bool]:
    if isinstance(raw, str):
        return raw, True
    if isinstance(raw, Mapping):
        selector = raw.get("selector", "table")
        selector = selector if isinstance(selector, str) and selector else "table"
        return selector, bool(raw.get("header", True))
    return "table", True


def _absolute(base: str, url: str) -> str:
    return urljoin(base, url) if base else url


def _str(value: object, default: str) -> str:
    return value if isinstance(value, str) and value else default
