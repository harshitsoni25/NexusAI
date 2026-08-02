"""An lxml-backed implementation of the parsed-document abstraction.

This module is the *only* place lxml is touched on the markup path. Extractors
program against the :class:`~nexusai.domain.ports.documents.Node` and
:class:`~nexusai.domain.ports.documents.ParsedDocument` protocols, so the
choice of lxml lives here and nowhere else; replacing it would change this file
alone.

Two node shapes implement the one protocol. An :class:`ElementNode` wraps an lxml
element and answers structural queries. A :class:`ValueNode` wraps a string that
an XPath expression produced -- ``//a/@href`` yields attribute strings, not
elements -- so that ``xpath`` can return a uniform sequence of nodes whose
``text()`` is the value, rather than leaking lxml's mixed result types upward.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from lxml import etree
from lxml.cssselect import SelectorError

from nexusai.domain.errors.exceptions import DocumentParseError
from nexusai.domain.ports.documents import Node


class ValueNode:
    """A node wrapping a scalar result from an XPath or attribute query.

    Has no structure of its own: its only content is the string it carries. This
    lets ``xpath`` return attribute and text results alongside element results
    without callers having to special-case them.
    """

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    @property
    def tag(self) -> str:
        """The pseudo-tag ``#value`` marking this as a scalar result."""
        return "#value"

    def text(self, *, strip: bool = True) -> str:
        """Return the wrapped string, stripped by default."""
        return self._value.strip() if strip else self._value

    def attribute(self, name: str) -> str | None:  # noqa: ARG002 - a scalar has none
        """A scalar has no attributes; always ``None``."""
        return None

    def attributes(self) -> Mapping[str, str]:
        """A scalar has no attributes; always empty."""
        return {}

    def select(self, css: str) -> Sequence[Node]:  # noqa: ARG002 - no descendants
        """A scalar has no descendants; always empty."""
        return ()

    def select_one(self, css: str) -> Node | None:  # noqa: ARG002 - no descendants
        """A scalar has no descendants; always ``None``."""
        return None

    def xpath(self, expression: str) -> Sequence[Node]:  # noqa: ARG002 - no tree
        """A scalar has no tree; always empty."""
        return ()

    def path(self) -> str:
        """A scalar has no path; always empty."""
        return ""


class ElementNode:
    """A node wrapping a single lxml element."""

    __slots__ = ("_element",)

    def __init__(self, element: etree._Element) -> None:
        self._element = element

    @property
    def tag(self) -> str:
        """The element's tag name, or ``#special`` for comments and the like."""
        tag = self._element.tag
        return tag if isinstance(tag, str) else "#special"

    def text(self, *, strip: bool = True) -> str:
        """Return the element's combined descendant text."""
        content = "".join(self._element.itertext())
        return content.strip() if strip else content

    def attribute(self, name: str) -> str | None:
        """Return an attribute value, or ``None`` if absent."""
        value = self._element.get(name)
        return value if value is None else str(value)

    def attributes(self) -> Mapping[str, str]:
        """Return all attributes as a plain mapping of strings."""
        return {str(key): str(value) for key, value in self._element.attrib.items()}

    def select(self, css: str) -> Sequence[Node]:
        """Return descendants matching a CSS selector."""
        try:
            matches = self._element.cssselect(css)
        except SelectorError as exc:
            raise DocumentParseError("Invalid CSS selector", selector=css, detail=str(exc)) from exc
        return tuple(ElementNode(match) for match in matches)

    def select_one(self, css: str) -> Node | None:
        """Return the first descendant matching a CSS selector, if any."""
        matches = self.select(css)
        return matches[0] if matches else None

    def xpath(self, expression: str) -> Sequence[Node]:
        """Return nodes matching an XPath expression.

        Element results become :class:`ElementNode`; string, attribute and
        numeric results become :class:`ValueNode`, so the return type is uniform.
        """
        try:
            results = self._element.xpath(expression)
        except etree.XPathError as exc:
            raise DocumentParseError(
                "Invalid XPath expression", selector=expression, detail=str(exc)
            ) from exc
        nodes: list[Node] = []
        for result in _iter_results(results):
            if isinstance(result, etree._Element):
                nodes.append(ElementNode(result))
            else:
                nodes.append(ValueNode(str(result)))
        return tuple(nodes)

    def path(self) -> str:
        """Return the element's absolute path within the tree, for provenance."""
        return str(self._element.getroottree().getpath(self._element))


def _iter_results(results: object) -> Sequence[object]:
    """Normalise lxml's variously-typed XPath return into a sequence."""
    if isinstance(results, list):
        return results
    return [results]
