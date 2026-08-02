"""JSON and plain-text parsers.

Neither format has a markup tree, so their node surface is empty and extraction
reads them through :meth:`data`. The JSON parser exposes the decoded structure
for path-based extraction; the text parser exposes the raw string for regular
expressions. Keeping them behind the same :class:`Parser` contract means the
extraction engine selects a parser by MIME type without special-casing formats.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from nexusai.domain.errors.exceptions import DocumentParseError
from nexusai.domain.model.retrieval import Document
from nexusai.domain.ports.documents import Node
from nexusai.infrastructure.parsing.tree import ValueNode
from nexusai.shared.types import JsonValue


class _DataDocument:
    """A parsed data document whose content is structured data or text."""

    __slots__ = ("_data", "_parser", "_text")

    def __init__(self, data: JsonValue, parser: str, text: str) -> None:
        self._data = data
        self._parser = parser
        self._text = text

    @property
    def parser(self) -> str:
        """The name of the parser that produced this document."""
        return self._parser

    @property
    def root(self) -> Node:
        """A scalar node carrying the document text; data formats have no tree."""
        return ValueNode(self._text)

    def select(self, css: str) -> Sequence[Node]:  # noqa: ARG002 - no tree to query
        """Data formats have no CSS tree; always empty."""
        return ()

    def select_one(self, css: str) -> Node | None:  # noqa: ARG002 - no tree to query
        """Data formats have no CSS tree; always ``None``."""
        return None

    def xpath(self, expression: str) -> Sequence[Node]:  # noqa: ARG002 - no tree
        """Data formats have no XPath tree; always empty."""
        return ()

    def data(self) -> JsonValue:
        """Return the decoded structure (JSON) or the raw text."""
        return self._data


class JsonParser:
    """Parses a JSON document into decoded data for path-based extraction."""

    name = "json"
    media_types = ("application/json", "application/ld+json", "text/json")

    def parse(self, document: Document) -> _DataDocument:
        """Parse ``document`` as JSON.

        Raises:
            DocumentParseError: If the content is not valid JSON.
        """
        text = document.text()
        try:
            data: JsonValue = json.loads(text) if text.strip() else None
        except json.JSONDecodeError as exc:
            raise DocumentParseError(
                "Failed to parse JSON",
                url=document.url,
                line=exc.lineno,
                column=exc.colno,
                detail=exc.msg,
            ) from exc
        return _DataDocument(data, self.name, text)


class TextParser:
    """Parses a document as plain text.

    The fallback parser: it never fails, so a document of an unrecognised type
    still yields something extraction can run a regular expression against.
    """

    name = "text"
    media_types = ("text/plain",)

    def parse(self, document: Document) -> _DataDocument:
        """Return the document's text, wrapped for extraction."""
        text = document.text()
        return _DataDocument(text, self.name, text)
