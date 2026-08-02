"""The extraction engine: parser selection and extractor coordination.

The engine turns a retrieved document into structured values. It picks a parser
by the document's MIME type, parses once, then runs a set of named extractors
against the resulting tree and merges their results. It applies no validation and
makes no network request; it is the orchestration seam between the parsers and
extractors this phase provides.
"""

from __future__ import annotations

from nexusai.application.extraction.engine import ExtractionEngine, ExtractionSpec

__all__ = ["ExtractionEngine", "ExtractionSpec"]
