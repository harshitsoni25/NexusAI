"""Selector-based extractors: CSS and XPath.

Both read the parsed-document abstraction and never touch a parser library. A
spec maps field names to selectors; the extractor resolves each against the tree
and records, per field, the selector used and the matched node's DOM path, so
every extracted value is traceable to where it came from.

The spec grammar is intentionally small. A field maps either to a selector
string -- take the first match's text -- or to a mapping that names an attribute
to read and whether to collect all matches rather than the first.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from nexusai.domain.model.extraction import (
    ExtractedValue,
    ExtractionMethod,
    ExtractionResult,
    FieldProvenance,
)
from nexusai.domain.ports.documents import Node, ParsedDocument
from nexusai.shared.types import JsonValue


def _read(node: Node, attribute: str | None) -> str | None:
    """Read a node's text, or a named attribute when ``attribute`` is given."""
    if attribute is None:
        return node.text()
    return node.attribute(attribute)


class _SelectorExtractor:
    """Shared logic for the CSS and XPath extractors, differing only in engine."""

    name: str
    _method: ExtractionMethod
    _use_xpath: bool

    def extract(self, parsed: ParsedDocument, spec: Mapping[str, object]) -> ExtractionResult:
        """Extract fields from ``parsed`` per ``spec``.

        Each entry in ``spec`` is a field name mapped to either a selector string
        or a mapping with keys ``selector``, ``attribute`` and ``many``.
        """
        fields: dict[str, ExtractedValue] = {}
        collections: dict[str, Sequence[ExtractedValue]] = {}
        for name, raw in spec.items():
            selector, attribute, many = _normalise(raw)
            matches = self._query(parsed, selector)
            if many:
                collections[name] = tuple(
                    self._value(node, selector, attribute) for node in matches
                )
                continue
            if not matches:
                fields[name] = ExtractedValue.missing(self._provenance(selector, attribute, None))
            else:
                fields[name] = self._value(matches[0], selector, attribute)
        return ExtractionResult(fields=fields, collections=collections)

    def _query(self, parsed: ParsedDocument, selector: str) -> Sequence[Node]:
        return parsed.xpath(selector) if self._use_xpath else parsed.select(selector)

    def _value(self, node: Node, selector: str, attribute: str | None) -> ExtractedValue:
        raw = _read(node, attribute)
        value: JsonValue = raw
        return ExtractedValue(
            value=value,
            found=raw is not None,
            provenance=self._provenance(selector, attribute, node),
        )

    def _provenance(
        self, selector: str, attribute: str | None, node: Node | None
    ) -> FieldProvenance:
        detail = selector if attribute is None else f"{selector}::attr({attribute})"
        return FieldProvenance(
            method=self._method,
            selector=detail,
            dom_path=node.path() if node is not None else None,
        )


class CssExtractor(_SelectorExtractor):
    """Extracts values by CSS selector."""

    name = "css"
    _method = ExtractionMethod.CSS
    _use_xpath = False


class XPathExtractor(_SelectorExtractor):
    """Extracts values by XPath expression."""

    name = "xpath"
    _method = ExtractionMethod.XPATH
    _use_xpath = True


def _normalise(raw: object) -> tuple[str, str | None, bool]:
    """Normalise a spec entry into (selector, attribute, many)."""
    if isinstance(raw, str):
        return raw, None, False
    if isinstance(raw, Mapping):
        selector = raw.get("selector")
        if not isinstance(selector, str) or not selector:
            raise ValueError("a selector spec must include a non-empty 'selector'")
        attribute = raw.get("attribute")
        if attribute is not None and not isinstance(attribute, str):
            raise ValueError("'attribute' must be a string when provided")
        return selector, attribute, bool(raw.get("many", False))
    raise TypeError(f"unsupported selector spec: {type(raw).__name__}")
