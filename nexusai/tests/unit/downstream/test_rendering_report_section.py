"""The report's browser-rendering section: assembly and escaped rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

from nexusai.application.downstream import ReportAssembler
from nexusai.domain.model.network import summarise_requests
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.domain.model.visual import VisualComparison, VisualStatus
from nexusai.infrastructure.reporting import HtmlReportRenderer

pytestmark = pytest.mark.component


def _visual() -> VisualComparison:
    return VisualComparison(
        difference_ratio=0.03,
        warning_threshold=0.01,
        fail_threshold=0.10,
        status=VisualStatus.WARNING,
    )


class TestAssembly:
    def test_no_rendering_section_for_static_dataset(self) -> None:
        report = ReportAssembler().assemble(ProcessedDataset(records=[]))
        assert report.rendering is None

    def test_rendering_section_built_from_browser_evidence(self) -> None:
        network = summarise_requests([{"url": "x", "method": "GET", "status": 200, "type": "xhr"}])
        report = ReportAssembler().assemble(
            ProcessedDataset(records=[]),
            visual=_visual(),
            network=network,
            staged_screenshot_count=4,
        )
        assert report.rendering is not None
        assert report.rendering.visual_status == "warning"
        assert report.rendering.staged_screenshot_count == 4
        assert report.rendering.network["total_requests"] == 1


class TestRendering:
    def test_html_shows_rendering_section(self, tmp_path: Path) -> None:
        network = summarise_requests(
            [{"url": "x", "method": "GET", "status": 500, "type": "fetch"}]
        )
        report = ReportAssembler().assemble(
            ProcessedDataset(records=[]),
            visual=_visual(),
            network=network,
            staged_screenshot_count=4,
        )
        HtmlReportRenderer(tmp_path).render(report, "r.html")
        html = (tmp_path / "r.html").read_text(encoding="utf-8")
        assert "Browser rendering" in html
        assert "warning" in html
        assert "API (XHR/fetch)" in html

    def test_static_report_has_no_rendering_section(self, tmp_path: Path) -> None:
        report = ReportAssembler().assemble(ProcessedDataset(records=[]))
        HtmlReportRenderer(tmp_path).render(report, "r.html")
        html = (tmp_path / "r.html").read_text(encoding="utf-8")
        assert "Browser rendering" not in html
