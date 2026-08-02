"""JSON report renderer.

Serialises the report model verbatim to JSON -- the machine-readable face of the
report, for automation, auditing and regression comparison. Because the model has
a stable ``to_dict`` and keys are sorted, two runs over identical inputs produce
byte-identical JSON that hashes the same, which is exactly what a regression check
needs.
"""

from __future__ import annotations

import json
from pathlib import Path

from nexusai.domain.model.persistence import ReportManifest
from nexusai.domain.model.report import Report
from nexusai.infrastructure.reporting.writer import (
    atomic_output,
    build_report_manifest,
    resolve_target,
)

_VERSION = "1.0"


class JsonReportRenderer:
    """Renders a report as machine-readable JSON."""

    report_format = "json"
    media_type = "application/json"

    def __init__(self, base_dir: Path) -> None:
        self._base = Path(base_dir)

    def render(self, report: Report, destination: str) -> ReportManifest:
        """Write ``report`` as JSON and return the manifest."""
        with atomic_output(self._base, destination) as temp:
            temp.write_text(
                json.dumps(report.to_dict(), sort_keys=True, indent=2, default=str),
                encoding="utf-8",
            )
        return build_report_manifest(
            resolve_target(self._base, destination),
            dataset_id=report.dataset.dataset_id,
            dataset_version=report.dataset.version,
            report_format=self.report_format,
            media_type=self.media_type,
            generator_version=_VERSION,
        )
