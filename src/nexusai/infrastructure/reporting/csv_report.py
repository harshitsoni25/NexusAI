"""CSV report renderer.

A report is nested by nature, so a single CSV would be lossy. Instead this
renderer writes several CSV files -- one per naturally tabular section
(validation issues, quality dimensions, provenance, artefacts) -- into a
directory, plus a small summary file for the flat top-level facts. Each section
keeps its own shape rather than being forced into one table. The manifest points
at the directory. Every cell passes through the formula-injection guard.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path

from nexusai.domain.model.persistence import ReportManifest
from nexusai.domain.model.report import Report
from nexusai.infrastructure.artifacts.integrity import content_hash
from nexusai.infrastructure.artifacts.paths import ensure_parent, safe_join
from nexusai.infrastructure.export.sanitize import neutralise

_VERSION = "1.0"


class CsvReportRenderer:
    """Renders the tabular sections of a report as a set of CSV files."""

    report_format = "csv"
    media_type = "text/csv"

    def __init__(self, base_dir: Path) -> None:
        self._base = Path(base_dir)

    def render(self, report: Report, destination: str) -> ReportManifest:
        """Write the report's tabular sections under ``destination`` as CSVs."""
        directory = safe_join(self._base, destination)
        directory.mkdir(parents=True, exist_ok=True)

        self._write_rows(
            directory / "summary.csv",
            ["metric", "value"],
            [
                ["dataset_id", report.dataset.dataset_id],
                ["version", report.dataset.version],
                ["record_count", report.dataset.record_count],
                ["validation_status", report.validation.status],
                ["quality_grade", report.quality.grade or ""],
                ["composite_score", report.quality.composite_score],
                ["changes_total", report.change.total],
            ],
        )
        self._write_dicts(
            directory / "validation_issues.csv",
            ["code", "severity", "message", "location"],
            report.validation.issues,
        )
        self._write_dicts(
            directory / "quality_dimensions.csv",
            ["dimension", "score", "weight"],
            report.quality.dimensions,
        )
        self._write_rows(
            directory / "provenance.csv",
            ["uri", "method", "retrieved_at", "content_hash"],
            [
                [
                    e.uri,
                    e.method,
                    e.retrieved_at.isoformat() if e.retrieved_at else "",
                    e.content_hash or "",
                ]
                for e in report.provenance
            ],
        )

        combined = b"".join(path.read_bytes() for path in sorted(directory.glob("*.csv")))
        return build_report_manifest_dir(
            directory, combined, report, self.report_format, self.media_type, _VERSION
        )

    def _write_rows(
        self, path: Path, header: Sequence[str], rows: Sequence[Sequence[object]]
    ) -> None:
        ensure_parent(path)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            for row in rows:
                writer.writerow([neutralise(str(cell)) for cell in row])

    def _write_dicts(
        self,
        path: Path,
        header: Sequence[str],
        rows: Sequence[Mapping[str, object]],
    ) -> None:
        self._write_rows(path, header, [[row.get(key, "") for key in header] for row in rows])


def build_report_manifest_dir(
    directory: Path,
    combined_bytes: bytes,
    report: Report,
    report_format: str,
    media_type: str,
    version: str,
) -> ReportManifest:
    """Build a report manifest for a directory-based (multi-file) report."""
    import uuid
    from datetime import UTC, datetime

    from nexusai.domain.model.persistence import OutcomeStatus
    from nexusai.domain.provenance.source import ArtifactReference

    return ReportManifest(
        report_id=uuid.uuid4().hex,
        dataset_id=report.dataset.dataset_id,
        dataset_version=report.dataset.version,
        report_format=report_format,
        artifact=ArtifactReference(
            locator=str(directory), media_type=media_type, size_bytes=len(combined_bytes)
        ),
        size_bytes=len(combined_bytes),
        content_hash=content_hash(combined_bytes),
        created_at=datetime.now(UTC),
        status=OutcomeStatus.SUCCESS,
        generator_version=version,
    )
