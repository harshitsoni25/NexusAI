"""Parquet exporter, behind the optional ``parquet`` extra.

Writes a columnar Parquet file for analytics workloads. pyarrow is imported
lazily, so importing this module never requires the optional dependency. Columns
are typed from the data where they are uniform; a column of mixed types, and any
nested value, is written as its JSON string form rather than guessed at, so the
file's schema is always well defined and no value is silently coerced or dropped.
"""

from __future__ import annotations

import json
from pathlib import Path

from nexusai.domain.errors.exceptions import ExportError
from nexusai.domain.model.persistence import DatasetVersion, ExportManifest
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.infrastructure.export.rows import column_order
from nexusai.infrastructure.export.writer import (
    atomic_output,
    build_manifest,
    export_identity,
    resolve_target,
)
from nexusai.shared.types import JsonValue

_VERSION = "1.0"


def _column_value(value: JsonValue) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, sort_keys=True, default=str)


class ParquetExporter:
    """Exports a dataset to a columnar Parquet file."""

    export_format = "parquet"
    media_type = "application/vnd.apache.parquet"

    def __init__(self, base_dir: Path, *, include_source: bool = True) -> None:
        self._base = Path(base_dir)
        self._include_source = include_source

    def export(
        self,
        dataset: ProcessedDataset,
        destination: str,
        *,
        version: DatasetVersion | None = None,
    ) -> ExportManifest:
        """Write ``dataset`` as Parquet and return the manifest.

        Raises:
            ExportError: If pyarrow is not installed.
        """
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError as exc:  # pragma: no cover - exercised via a stub
            raise ExportError("Parquet export requires the 'parquet' extra (pyarrow)") from exc

        columns = column_order(dataset, include_source=self._include_source)
        table_data: dict[str, list[object]] = {column: [] for column in columns}
        for record in dataset.records:
            for column in columns:
                if column.endswith("_source_uri"):
                    table_data[column].append(
                        record.source.uri if record.source is not None else None
                    )
                else:
                    table_data[column].append(_column_value(record.value(column)))

        table = pa.table(table_data)
        with atomic_output(self._base, destination) as temp:
            pq.write_table(table, temp)
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
