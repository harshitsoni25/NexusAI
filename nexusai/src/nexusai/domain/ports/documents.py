"""Contracts for parsing documents and extracting values.

The parsed-document abstraction is the seam that keeps extraction independent of
any parser library. A :class:`Parser` turns a :class:`Document` into a
:class:`ParsedDocument`; extractors then query that abstraction through
:class:`Node`, never touching lxml, an HTML library or a JSON path package
directly. Swapping the parser swaps the tree implementation without extraction
noticing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.retrieval import Document
from nexusai.shared.types import JsonValue


@runtime_checkable
class Node(Protocol):
    """A single element in a parsed document tree.

    The query surface extractors rely on. A node can be searched by CSS or XPath,
    yield its text and attributes, and report its own path -- everything an
    extractor needs, expressed without reference to how the tree is stored.
    """

    @property
    def tag(self) -> str:
        """The element's tag name."""
        ...

    def text(self, *, strip: bool = True) -> str:
        """Return the element's combined text content."""
        ...

    def attribute(self, name: str) -> str | None:
        """Return an attribute value, or ``None`` if absent."""
        ...

    def attributes(self) -> Mapping[str, str]:
        """Return all attributes of the element."""
        ...

    def select(self, css: str) -> Sequence[Node]:
        """Return descendants matching a CSS selector."""
        ...

    def select_one(self, css: str) -> Node | None:
        """Return the first descendant matching a CSS selector, if any."""
        ...

    def xpath(self, expression: str) -> Sequence[Node]:
        """Return nodes matching an XPath expression."""
        ...

    def path(self) -> str:
        """Return a stable path to this node, for provenance."""
        ...


@runtime_checkable
class ParsedDocument(Protocol):
    """A document parsed into a queryable tree.

    Exposes the same query surface as :class:`Node` from the document root, plus
    the name of the parser that produced it, so provenance can record which
    parser was responsible.
    """

    @property
    def parser(self) -> str:
        """The name of the parser that produced this tree."""
        ...

    @property
    def root(self) -> Node:
        """The root node of the tree."""
        ...

    def select(self, css: str) -> Sequence[Node]:
        """Return nodes matching a CSS selector from the root."""
        ...

    def select_one(self, css: str) -> Node | None:
        """Return the first node matching a CSS selector, if any."""
        ...

    def xpath(self, expression: str) -> Sequence[Node]:
        """Return nodes matching an XPath expression from the root."""
        ...

    def data(self) -> JsonValue:
        """Return the document as structured data, for data formats.

        Meaningful for JSON and similar formats; markup parsers return the
        document text. Extraction by JSON path uses this rather than the node
        tree.
        """
        ...


@runtime_checkable
class Parser(Protocol):
    """Converts a retrieved document into a parsed tree.

    A parser owns one family of formats and declares the media types it handles,
    so a parser registry can pick one by the document's MIME type. It performs no
    extraction: it produces the tree and stops.
    """

    @property
    def name(self) -> str:
        """A stable identifier used to register and select the parser."""
        ...

    @property
    def media_types(self) -> Sequence[str]:
        """The MIME types this parser handles."""
        ...

    def parse(self, document: Document) -> ParsedDocument:
        """Parse ``document`` into a queryable tree.

        Raises:
            DocumentParseError: If the content cannot be parsed as the expected
                format.
        """
        ...


@runtime_checkable
class Extractor(Protocol):
    """Extracts values from a parsed document.

    An extractor implements one mechanism -- CSS, XPath, regex, JSON path, tables
    -- against the :class:`ParsedDocument` abstraction. It reads structure and
    produces :class:`ExtractionResult`; it makes no network request and applies
    no validation.
    """

    @property
    def name(self) -> str:
        """A stable identifier used to register and select the extractor."""
        ...

    def extract(self, parsed: ParsedDocument, spec: Mapping[str, object]) -> ExtractionResult:
        """Extract values from ``parsed`` according to ``spec``.

        Args:
            parsed: The document tree to read.
            spec: A declarative description of what to extract -- field names to
                selectors -- interpreted by the specific extractor.
        """
        ...
