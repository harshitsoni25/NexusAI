"""JSON and NDJSON exporters.

Two exporters share a module because they answer the same need at different
scales. :class:`JsonExporter` writes one JSON document preserving nested
structure, suitable when the whole dataset fits comfortably in memory.
:class:`NdjsonExporter` writes one JSON object per line, which streams: it never
holds more than a single record's serialisation at once, so it exports a dataset
of any size. Both serialise deterministically -- sorted keys -- so identical
inputs produce byte-identical output that hashes the same, aiding reproducibility.
"""

from __future__ import annotations

import json
from pathlib import Path

from nexusai.domain.model.persistence import DatasetVersion, ExportManifest
from nexusai.domain.model.processing import ProcessedDataset, ProcessedRecord
from nexusai.infrastructure.export.writer import (
    atomic_output,
    build_manifest,
    export_identity,
    resolve_target,
)

_VERSION = "1.0"


def _record_payload(record: ProcessedRecord) -> dict[str, object]:
    payload: dict[str, object] = {
        "identity": record.identity,
        "fields": {name: field.value for name, field in record.fields.items()},
        "raw": {name: field.raw_value for name, field in record.fields.items()},
    }
    if record.source is not None:
        payload["source"] = record.source.to_dict()
    return payload


class JsonExporter:
    """Exports a dataset as a single JSON document preserving nesting."""

    export_format = "json"
    media_type = "application/json"

    def __init__(self, base_dir: Path, *, indent: int | None = None) -> None:
        self._base = Path(base_dir)
        self._indent = indent

    def export(
        self,
        dataset: ProcessedDataset,
        destination: str,
        *,
        version: DatasetVersion | None = None,
    ) -> ExportManifest:
        """Write ``dataset`` as JSON and return the manifest."""
        payload = [_record_payload(record) for record in dataset.records]
        with atomic_output(self._base, destination) as temp:
            temp.write_text(
                json.dumps(payload, sort_keys=True, indent=self._indent, default=str),
                encoding="utf-8",
            )
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


class NdjsonExporter:
    """Exports a dataset as newline-delimited JSON, one record per line."""

    export_format = "ndjson"
    media_type = "application/x-ndjson"

    def __init__(self, base_dir: Path) -> None:
        self._base = Path(base_dir)

    def export(
        self,
        dataset: ProcessedDataset,
        destination: str,
        *,
        version: DatasetVersion | None = None,
    ) -> ExportManifest:
        """Stream ``dataset`` as NDJSON and return the manifest."""
        with (
            atomic_output(self._base, destination) as temp,
            temp.open("w", encoding="utf-8") as handle,
        ):
            for record in dataset.records:
                line = json.dumps(_record_payload(record), sort_keys=True, default=str)
                handle.write(line + "\n")
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
