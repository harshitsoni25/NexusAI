"""CSV exporter.

Writes a processed dataset as CSV, streaming record by record so a dataset larger
than memory exports without loading in full. Every field value passes through the
formula-injection guard, because a CSV is routinely opened in a spreadsheet.
Dialect details -- delimiter, quoting, line terminator, encoding, null
representation -- are configurable, and the column order is deterministic so the
same dataset always yields the same schema.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Literal

from nexusai.domain.model.persistence import DatasetVersion, ExportManifest
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.infrastructure.export.rows import column_order, record_to_row
from nexusai.infrastructure.export.sanitize import neutralise
from nexusai.infrastructure.export.writer import (
    atomic_output,
    build_manifest,
    export_identity,
    resolve_target,
)

_VERSION = "1.0"


class CsvExporter:
    """Exports a dataset to CSV with configurable dialect and safety."""

    export_format = "csv"
    media_type = "text/csv"

    def __init__(
        self,
        base_dir: Path,
        *,
        delimiter: str = ",",
        quoting: Literal[0, 1, 2, 3, 4, 5] = csv.QUOTE_MINIMAL,
        line_terminator: str = "\r\n",
        encoding: str = "utf-8",
        null: str = "",
        include_header: bool = True,
        include_source: bool = True,
    ) -> None:
        self._base = Path(base_dir)
        self._delimiter = delimiter
        self._quoting = quoting
        self._line_terminator = line_terminator
        self._encoding = encoding
        self._null = null
        self._include_header = include_header
        self._include_source = include_source

    def export(
        self,
        dataset: ProcessedDataset,
        destination: str,
        *,
        version: DatasetVersion | None = None,
    ) -> ExportManifest:
        """Write ``dataset`` to ``destination`` as CSV and return the manifest."""
        columns = column_order(dataset, include_source=self._include_source)
        with (
            atomic_output(self._base, destination) as temp,
            temp.open("w", encoding=self._encoding, newline="") as handle,
        ):
            writer = csv.writer(
                handle,
                delimiter=self._delimiter,
                quoting=self._quoting,
                lineterminator=self._line_terminator,
            )
            if self._include_header:
                writer.writerow(columns)
            for record in dataset.records:
                row = record_to_row(record, columns, null=self._null)
                writer.writerow([neutralise(row[column]) for column in columns])
        dataset_id, dataset_version = export_identity(version)
        return build_manifest(
            resolve_target(self._base, destination),
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            export_format=self.export_format,
            media_type=self.media_type,
            record_count=len(dataset.records),
            duration_seconds=0.0,
            exporter_version=_VERSION,
        )
