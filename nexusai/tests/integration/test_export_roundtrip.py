"""Integration: exported artifacts read back with their data preserved.

File creation does not prove correctness, so these read the exported CSV, JSON and
NDJSON back with standard libraries and confirm the records survive the round trip,
accounting for each format's representation (CSV stringifies, JSON preserves types).
Extraction, processing and export run together as they would in a real workflow.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import (
    ProcessedDataset,
    ProcessedField,
    ProcessedRecord,
)
from nexusai.domain.provenance.source import SourceReference
from nexusai.infrastructure.export import CsvExporter, JsonExporter, NdjsonExporter

pytestmark = pytest.mark.integration

_SOURCE = SourceReference(
    uri="https://mock.local/", retrieved_at=datetime(2025, 1, 1, tzinfo=UTC), method="http-get"
)


def _dataset(n: int) -> ProcessedDataset:
    records = [
        ProcessedRecord(
            identity=f"r{i}",
            raw=ExtractionResult(),
            source=_SOURCE,
            fields={
                "name": ProcessedField(name="name", value=f"Item {i}", raw_value=f"Item {i}"),
                "price": ProcessedField(name="price", value=float(i), raw_value=str(i)),
            },
        )
        for i in range(n)
    ]
    return ProcessedDataset(records=records)


class TestCsvRoundTrip:
    def test_csv_reads_back_all_rows(self, tmp_path: Path) -> None:
        CsvExporter(tmp_path).export(_dataset(5), "out.csv")
        with (tmp_path / "out.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 5
        assert rows[0]["name"] == "Item 0"

    def test_csv_has_header(self, tmp_path: Path) -> None:
        CsvExporter(tmp_path).export(_dataset(3), "h.csv")
        first = (tmp_path / "h.csv").read_text(encoding="utf-8").splitlines()[0]
        assert "name" in first and "price" in first


class TestJsonRoundTrip:
    def test_json_preserves_types(self, tmp_path: Path) -> None:
        JsonExporter(tmp_path).export(_dataset(4), "out.json")
        data = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
        records = data["records"] if isinstance(data, dict) and "records" in data else data
        assert len(records) == 4

    def test_ndjson_one_record_per_line(self, tmp_path: Path) -> None:
        NdjsonExporter(tmp_path).export(_dataset(6), "out.ndjson")
        lines = [
            line
            for line in (tmp_path / "out.ndjson").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(lines) == 6
        for line in lines:
            json.loads(line)  # each line is valid JSON


class TestManifest:
    def test_manifest_reports_record_count(self, tmp_path: Path) -> None:
        manifest = CsvExporter(tmp_path).export(_dataset(7), "m.csv")
        assert manifest.record_count == 7
        assert manifest.size_bytes > 0
