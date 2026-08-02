"""PDF report renderer, behind the optional ``pdf`` extra.

Renders the same report model as the other formats to a paginated PDF using
reportlab, imported lazily so importing this module never requires the optional
dependency. There is no PDF-specific report logic: the renderer reads the model's
summaries and lays them out, exactly as the HTML and JSON renderers do, so the
four outputs cannot drift out of agreement.
"""

from __future__ import annotations

from pathlib import Path

from nexusai.domain.errors.exceptions import ReportError
from nexusai.domain.model.persistence import ReportManifest
from nexusai.domain.model.report import Report
from nexusai.infrastructure.reporting.writer import (
    atomic_output,
    build_report_manifest,
    resolve_target,
)

_VERSION = "1.0"


class PdfReportRenderer:
    """Renders a report as a paginated PDF."""

    report_format = "pdf"
    media_type = "application/pdf"

    def __init__(self, base_dir: Path) -> None:
        self._base = Path(base_dir)

    def render(self, report: Report, destination: str) -> ReportManifest:
        """Write ``report`` as a PDF and return the manifest.

        Raises:
            ReportError: If reportlab is not installed.
        """
        try:
            from reportlab.lib.pagesizes import LETTER
            from reportlab.lib.units import inch
            from reportlab.pdfgen import canvas
        except ImportError as exc:  # pragma: no cover - exercised via a stub
            raise ReportError("PDF reporting requires the 'pdf' extra (reportlab)") from exc

        with atomic_output(self._base, destination) as temp:
            pdf = canvas.Canvas(str(temp), pagesize=LETTER)
            width, height = LETTER
            cursor = _Cursor(pdf, margin=inch, top=height - inch, width=width)
            cursor.heading("Nexus AI Data Report")
            cursor.line(f"Generated: {report.generated_at.isoformat()}")
            cursor.line(f"Framework: {report.framework_version}")
            cursor.gap()

            cursor.subheading("Executive Summary")
            cursor.line(f"Records: {report.dataset.record_count}")
            cursor.line(f"Validation: {report.validation.status}")
            cursor.line(f"Quality grade: {report.quality.grade or 'n/a'}")
            cursor.line(f"Composite score: {report.quality.composite_score:.3f}")
            cursor.line(f"Changes: {report.change.total}")
            cursor.gap()

            cursor.subheading("Validation")
            cursor.line(
                f"Passing {report.validation.passing_records}, "
                f"warnings {report.validation.warning_records}, "
                f"failing {report.validation.failing_records}"
            )
            for issue in report.validation.issues[:40]:
                cursor.line(
                    f"- [{issue.get('severity','')}] {issue.get('code','')}: "
                    f"{issue.get('message','')}",
                    indent=12,
                )
            cursor.gap()

            cursor.subheading("Quality Dimensions")
            for dim in report.quality.dimensions:
                raw_score = dim.get("score", 0.0)
                score = float(raw_score) if isinstance(raw_score, (int, float)) else 0.0
                cursor.line(
                    f"- {dim.get('dimension','')}: {score:.3f}",
                    indent=12,
                )
            cursor.gap()

            cursor.subheading("Source Provenance")
            for entry in report.provenance[:40]:
                cursor.line(f"- {entry.method}: {entry.uri}", indent=12)

            pdf.save()

        return build_report_manifest(
            resolve_target(self._base, destination),
            dataset_id=report.dataset.dataset_id,
            dataset_version=report.dataset.version,
            report_format=self.report_format,
            media_type=self.media_type,
            generator_version=_VERSION,
        )


class _Cursor:
    """A tiny stateful layout helper that paginates as it runs out of vertical room."""

    def __init__(self, pdf: object, *, margin: float, top: float, width: float) -> None:
        self._pdf = pdf
        self._margin = margin
        self._width = width
        self._y = top
        self._top = top

    def heading(self, text: str) -> None:
        self._pdf.setFont("Helvetica-Bold", 16)  # type: ignore[attr-defined]
        self._draw(text)
        self._y -= 6

    def subheading(self, text: str) -> None:
        self._ensure(30)
        self._pdf.setFont("Helvetica-Bold", 12)  # type: ignore[attr-defined]
        self._draw(text)

    def line(self, text: str, *, indent: float = 0) -> None:
        self._ensure(16)
        self._pdf.setFont("Helvetica", 10)  # type: ignore[attr-defined]
        self._pdf.drawString(  # type: ignore[attr-defined]
            self._margin + indent, self._y, text[:110]
        )
        self._y -= 14

    def gap(self) -> None:
        self._y -= 8

    def _draw(self, text: str) -> None:
        self._ensure(20)
        self._pdf.drawString(self._margin, self._y, text)  # type: ignore[attr-defined]
        self._y -= 18

    def _ensure(self, needed: float) -> None:
        if self._y - needed < self._margin:
            self._pdf.showPage()  # type: ignore[attr-defined]
            self._y = self._top
