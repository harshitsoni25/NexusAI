"""Document parsers producing the parsed-document abstraction.

Each parser converts a retrieved :class:`~nexusai.domain.model.retrieval.Document`
into a queryable tree or a decoded-data view, implementing the
:class:`~nexusai.domain.ports.documents.Parser` contract. Extraction reads the
abstraction the parsers produce and never a parser library, so a parser can be
swapped without extraction noticing.
"""

from __future__ import annotations

from nexusai.infrastructure.parsing.markup import HtmlParser, XmlParser
from nexusai.infrastructure.parsing.structured import JsonParser, TextParser

__all__ = ["HtmlParser", "JsonParser", "TextParser", "XmlParser"]
