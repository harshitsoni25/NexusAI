"""Application service for exporting datasets.

Holds a registry of exporters keyed by format and dispatches an export request to
the right one, returning its manifest. It adds no format logic of its own -- an
exporter does the writing -- and it never queries persistence or re-runs Phase 5;
it simply routes a dataset to a chosen exporter. Requesting an unregistered format
is an explicit error rather than a silent no-op.
"""

from __future__ import annotations

from nexusai.domain.errors.exceptions import ExportError
from nexusai.domain.model.persistence import DatasetVersion, ExportManifest
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.domain.ports.storage import DatasetExporter


class ExportService:
    """Dispatches export requests to registered exporters by format."""

    def __init__(self) -> None:
        self._exporters: dict[str, DatasetExporter] = {}

    def register(self, exporter: DatasetExporter) -> None:
        """Register ``exporter`` under its declared format."""
        self._exporters[exporter.export_format] = exporter

    def formats(self) -> list[str]:
        """Return the registered export formats, sorted."""
        return sorted(self._exporters)

    def export(
        self,
        dataset: ProcessedDataset,
        export_format: str,
        destination: str,
        *,
        version: DatasetVersion | None = None,
    ) -> ExportManifest:
        """Export ``dataset`` in ``export_format`` to ``destination``.

        Raises:
            ExportError: If no exporter is registered for ``export_format``.
        """
        exporter = self._exporters.get(export_format)
        if exporter is None:
            raise ExportError(
                "No exporter registered for format",
                requested=export_format,
                available=self.formats(),
            )
        return exporter.export(dataset, destination, version=version)
