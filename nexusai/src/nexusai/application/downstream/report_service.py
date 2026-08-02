"""Application service for rendering reports.

Holds a registry of report renderers keyed by format and dispatches a render
request. Like the export service, it adds no presentation logic and never
recalculates anything: it routes a report model to a chosen renderer. Requesting
an unregistered format is an explicit error.
"""

from __future__ import annotations

from nexusai.domain.errors.exceptions import ReportError
from nexusai.domain.model.persistence import ReportManifest
from nexusai.domain.model.report import Report
from nexusai.domain.ports.storage import ReportRenderer


class ReportService:
    """Dispatches render requests to registered renderers by format."""

    def __init__(self) -> None:
        self._renderers: dict[str, ReportRenderer] = {}

    def register(self, renderer: ReportRenderer) -> None:
        """Register ``renderer`` under its declared format."""
        self._renderers[renderer.report_format] = renderer

    def formats(self) -> list[str]:
        """Return the registered report formats, sorted."""
        return sorted(self._renderers)

    def render(self, report: Report, report_format: str, destination: str) -> ReportManifest:
        """Render ``report`` in ``report_format`` to ``destination``.

        Raises:
            ReportError: If no renderer is registered for ``report_format``.
        """
        renderer = self._renderers.get(report_format)
        if renderer is None:
            raise ReportError(
                "No renderer registered for format",
                requested=report_format,
                available=self.formats(),
            )
        return renderer.render(report, destination)
