"""Reporting: assembly, every renderer, HTML escaping, and secret redaction."""

from __future__ import annotations

from pathlib import Path

import pytest

from downstream_builders import make_dataset, make_record
from nexusai.application.downstream import ReportAssembler, ReportService
from nexusai.domain.model.persistence import DatasetId, DatasetVersion
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.domain.policy.redaction import REDACTED, SecretRedactor
from nexusai.infrastructure.reporting import (
    CsvReportRenderer,
    HtmlReportRenderer,
    JsonReportRenderer,
    PdfReportRenderer,
)


def _version() -> DatasetVersion:
    return DatasetVersion(dataset_id=DatasetId.of("cat"), version=1, run_id="r1")


class TestAssembler:
    def test_copies_phase5_results_without_recomputing(self, dataset: ProcessedDataset) -> None:
        report = ReportAssembler().assemble(dataset, version=_version())
        assert report.quality.grade == "B"
        assert report.change.total == 3
        assert report.validation.status in {"PASS", "WARNING", "FAIL"}

    def test_preserves_provenance_entries(self, dataset: ProcessedDataset) -> None:
        report = ReportAssembler().assemble(dataset, version=_version())
        assert any("shop" in entry.uri for entry in report.provenance)

    def test_carries_errors_and_warnings(self, dataset: ProcessedDataset) -> None:
        report = ReportAssembler().assemble(
            dataset, version=_version(), errors=["e"], warnings=["w"]
        )
        assert report.errors == ("e",)
        assert report.warnings == ("w",)


class TestRenderers:
    def test_json_report_is_deterministic(self, dataset: ProcessedDataset, out_dir: Path) -> None:
        report = ReportAssembler().assemble(dataset, version=_version())
        first = JsonReportRenderer(out_dir).render(report, "a.json")
        second = JsonReportRenderer(out_dir).render(report, "b.json")
        assert first.content_hash == second.content_hash

    def test_html_report_has_chart_and_sections(
        self, dataset: ProcessedDataset, out_dir: Path
    ) -> None:
        report = ReportAssembler().assemble(dataset, version=_version())
        HtmlReportRenderer(out_dir).render(report, "a.html")
        html = (out_dir / "a.html").read_text()
        assert "<svg" in html
        assert "Executive Summary" in html

    def test_csv_report_writes_section_files(
        self, dataset: ProcessedDataset, out_dir: Path
    ) -> None:
        report = ReportAssembler().assemble(dataset, version=_version())
        CsvReportRenderer(out_dir).render(report, "report")
        assert (out_dir / "report" / "validation_issues.csv").exists()
        assert (out_dir / "report" / "quality_dimensions.csv").exists()

    def test_pdf_report_is_generated(self, dataset: ProcessedDataset, out_dir: Path) -> None:
        pytest.importorskip("reportlab")
        report = ReportAssembler().assemble(dataset, version=_version())
        manifest = PdfReportRenderer(out_dir).render(report, "a.pdf")
        assert (out_dir / "a.pdf").read_bytes().startswith(b"%PDF")
        assert manifest.size_bytes > 0

    def test_service_dispatches_by_format(self, dataset: ProcessedDataset, out_dir: Path) -> None:
        service = ReportService()
        service.register(JsonReportRenderer(out_dir))
        service.register(HtmlReportRenderer(out_dir))
        report = ReportAssembler().assemble(dataset, version=_version())
        assert service.render(report, "json", "a.json").report_format == "json"
        assert service.formats() == ["html", "json"]


class TestHtmlEscaping:
    def test_untrusted_markup_is_escaped(self, out_dir: Path) -> None:
        dataset = type(make_dataset())(
            records=[make_record("p1", "<script>alert(1)</script>", 1, "https://x/1")]
        )
        report = ReportAssembler().assemble(dataset, version=_version())
        HtmlReportRenderer(out_dir).render(report, "a.html")
        html = (out_dir / "a.html").read_text()
        assert "<script>alert(1)</script>" not in html

    def test_error_text_is_escaped(self, dataset: ProcessedDataset, out_dir: Path) -> None:
        report = ReportAssembler().assemble(
            dataset, version=_version(), errors=["<img src=x onerror=1>"]
        )
        HtmlReportRenderer(out_dir).render(report, "a.html")
        html = (out_dir / "a.html").read_text()
        assert "<img src=x onerror=1>" not in html
        assert "&lt;img" in html


class TestSecretRedaction:
    def test_secret_keys_are_redacted(self) -> None:
        result = SecretRedactor().redact({"host": "db", "password": "hunter2"})
        assert result["host"] == "db"
        assert result["password"] == REDACTED

    def test_nested_secrets_are_redacted(self) -> None:
        result = SecretRedactor().redact({"database": {"api_key": "k", "url": "u"}})
        nested = result["database"]
        assert isinstance(nested, dict)
        assert nested["api_key"] == REDACTED
        assert nested["url"] == "u"

    def test_whole_secret_subtree_is_redacted(self) -> None:
        result = SecretRedactor().redact({"auth": {"api_key": "k", "url": "u"}})
        assert result["auth"] == REDACTED

    def test_case_insensitive_matching(self) -> None:
        result = SecretRedactor().redact({"DB_PASSWORD": "x", "ApiKey": "y"})
        assert result["DB_PASSWORD"] == REDACTED
        assert result["ApiKey"] == REDACTED


class TestReportServiceErrors:
    def test_unknown_format_raises(self, dataset: ProcessedDataset, out_dir: Path) -> None:
        from nexusai.domain.errors.exceptions import ReportError

        service = ReportService()
        service.register(JsonReportRenderer(out_dir))
        report = ReportAssembler().assemble(dataset, version=_version())
        with pytest.raises(ReportError):
            service.render(report, "xml", "a.xml")


class TestReportArtifactsSection:
    def test_html_lists_artifacts_and_performance(
        self, dataset: ProcessedDataset, out_dir: Path
    ) -> None:
        from nexusai.domain.model.report import ReportArtifact

        report = ReportAssembler().assemble(
            dataset,
            version=_version(),
            artifacts=[
                ReportArtifact(
                    artifact_type="screenshot",
                    locator="/a/shot.png",
                    media_type="image/png",
                )
            ],
            performance={"persist_seconds": 0.01},
        )
        HtmlReportRenderer(out_dir).render(report, "a.html")
        html = (out_dir / "a.html").read_text()
        assert "shot.png" in html
        assert "persist_seconds" in html
