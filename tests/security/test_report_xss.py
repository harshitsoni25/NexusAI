"""Security: HTML reports treat scraped/error content as untrusted and escape it."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from nexusai.application.downstream import ReportAssembler
from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import (
    ProcessedDataset,
    ProcessedField,
    ProcessedRecord,
)
from nexusai.domain.provenance.source import SourceReference
from nexusai.infrastructure.reporting import HtmlReportRenderer

pytestmark = pytest.mark.security

_SOURCE = SourceReference(
    uri="https://mock.local/", retrieved_at=datetime(2025, 1, 1, tzinfo=UTC), method="http-get"
)
_XSS = "<script>alert('xss')</script>"


def _dataset() -> ProcessedDataset:
    record = ProcessedRecord(
        identity="r0",
        raw=ExtractionResult(),
        source=_SOURCE,
        fields={"name": ProcessedField(name="name", value="safe", raw_value="safe")},
    )
    return ProcessedDataset(records=[record])


class TestReportEscaping:
    def test_untrusted_error_text_is_escaped(self, tmp_path: Path) -> None:
        report = ReportAssembler().assemble(_dataset(), errors=[_XSS])
        HtmlReportRenderer(tmp_path).render(report, "r.html")
        html = (tmp_path / "r.html").read_text(encoding="utf-8")
        assert _XSS not in html
        assert "&lt;script&gt;" in html

    def test_untrusted_warning_text_is_escaped(self, tmp_path: Path) -> None:
        report = ReportAssembler().assemble(_dataset(), warnings=[_XSS])
        HtmlReportRenderer(tmp_path).render(report, "r.html")
        html = (tmp_path / "r.html").read_text(encoding="utf-8")
        assert "<script>alert" not in html

    def test_report_root_is_wellformed(self, tmp_path: Path) -> None:
        report = ReportAssembler().assemble(_dataset())
        HtmlReportRenderer(tmp_path).render(report, "r.html")
        html = (tmp_path / "r.html").read_text(encoding="utf-8").strip()
        assert html.startswith(("<!DOCTYPE", "<!doctype", "<html"))
