"""HTML and XML parsers producing the lxml-backed tree.

Both formats parse into the same node abstraction, so extraction cannot tell an
HTML document from an XML one -- it queries the tree either way. The parsers
differ only in how lenient they are: HTML parsing recovers from the malformed
markup that is the norm on the public web, while XML parsing recovers too but is
reported distinctly so that a genuinely broken feed is visible.
"""

from __future__ import annotations

from collections.abc import Sequence

from lxml import etree, html

from nexusai.domain.errors.exceptions import DocumentParseError
from nexusai.domain.model.retrieval import Document
from nexusai.domain.ports.documents import Node
from nexusai.infrastructure.parsing.tree import ElementNode
from nexusai.shared.types import JsonValue


class _TreeDocument:
    """A parsed markup document exposing the node query surface from its root."""

    __slots__ = ("_parser", "_root", "_text")

    def __init__(self, root: etree._Element, parser: str, text: str) -> None:
        self._root = ElementNode(root)
        self._parser = parser
        self._text = text

    @property
    def parser(self) -> str:
        """The name of the parser that produced this tree."""
        return self._parser

    @property
    def root(self) -> Node:
        """The root node of the tree."""
        return self._root

    def select(self, css: str) -> Sequence[Node]:
        """Return nodes matching a CSS selector from the root."""
        return self._root.select(css)

    def select_one(self, css: str) -> Node | None:
        """Return the first node matching a CSS selector, if any."""
        return self._root.select_one(css)

    def xpath(self, expression: str) -> Sequence[Node]:
        """Return nodes matching an XPath expression from the root."""
        return self._root.xpath(expression)

    def data(self) -> JsonValue:
        """Return the document text; markup has no structured-data view."""
        return self._text


class HtmlParser:
    """Parses HTML into the lxml-backed tree, recovering from malformed markup."""

    name = "html"
    media_types = ("text/html", "application/xhtml+xml")

    def parse(self, document: Document) -> _TreeDocument:
        """Parse ``document`` as HTML.

        Raises:
            DocumentParseError: If the content yields no parseable root at all,
                which for HTML means it was empty rather than merely malformed.
        """
        text = document.text()
        try:
            root = html.fromstring(text) if text.strip() else None
        except (etree.ParserError, ValueError) as exc:
            raise DocumentParseError(
                "Failed to parse HTML", url=document.url, detail=str(exc)
            ) from exc
        if root is None:
            raise DocumentParseError("HTML document is empty", url=document.url)
        return _TreeDocument(root, self.name, text)


class XmlParser:
    """Parses XML into the lxml-backed tree."""

    name = "xml"
    media_types = ("application/xml", "text/xml", "application/rss+xml", "application/atom+xml")

    def parse(self, document: Document) -> _TreeDocument:
        """Parse ``document`` as XML.

        Raises:
            DocumentParseError: If the content is not well-formed enough to yield
                a root element.
        """
        content = document.content or document.text().encode("utf-8")
        parser = etree.XMLParser(recover=True, resolve_entities=False, no_network=True)
        try:
            root = etree.fromstring(content, parser=parser)
        except etree.XMLSyntaxError as exc:
            raise DocumentParseError(
                "Failed to parse XML", url=document.url, detail=str(exc)
            ) from exc
        if root is None:
            raise DocumentParseError("XML document is empty or malformed", url=document.url)
        return _TreeDocument(root, self.name, document.text())
