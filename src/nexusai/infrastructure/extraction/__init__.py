"""Extraction mechanisms operating on the parsed-document abstraction.

Every extractor here reads a
:class:`~nexusai.domain.ports.documents.ParsedDocument` and returns an
:class:`~nexusai.domain.model.extraction.ExtractionResult`. None makes a
network request, none applies validation, and none imports a parser library --
they query the tree and data abstractions the parsers expose. New mechanisms are
added by registering another extractor, never by editing the engine.
"""

from __future__ import annotations

from nexusai.infrastructure.extraction.patterns import (
    JsonPathExtractor,
    RegexExtractor,
)
from nexusai.infrastructure.extraction.selectors import CssExtractor, XPathExtractor
from nexusai.infrastructure.extraction.structure import (
    AttributeExtractor,
    ImageExtractor,
    LinkExtractor,
    MetadataExtractor,
    TableExtractor,
)

__all__ = [
    "AttributeExtractor",
    "CssExtractor",
    "ImageExtractor",
    "JsonPathExtractor",
    "LinkExtractor",
    "MetadataExtractor",
    "RegexExtractor",
    "TableExtractor",
    "XPathExtractor",
]
