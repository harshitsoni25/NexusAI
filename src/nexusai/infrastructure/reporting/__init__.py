"""Report renderers turning the report model into presentation artefacts.

HTML, JSON and CSV are always available; PDF lives behind the ``pdf`` extra and
imports reportlab lazily. Every renderer consumes the same stable report model,
so the outputs agree and none recalculates a Phase 5 result.
"""

from __future__ import annotations

from nexusai.infrastructure.reporting.csv_report import CsvReportRenderer
from nexusai.infrastructure.reporting.html_report import HtmlReportRenderer
from nexusai.infrastructure.reporting.json_report import JsonReportRenderer
from nexusai.infrastructure.reporting.pdf_report import PdfReportRenderer

__all__ = [
    "CsvReportRenderer",
    "HtmlReportRenderer",
    "JsonReportRenderer",
    "PdfReportRenderer",
]
