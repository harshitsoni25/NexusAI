"""Export: every format, formula injection, Excel limits, atomic writes, manifests."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from downstream_builders import make_dataset, make_record
from nexusai.domain.errors.exceptions import ExportError
from nexusai.domain.model.persistence import ExportManifest
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.infrastructure.export import (
    CsvExporter,
    ExcelExporter,
    JsonExporter,
    NdjsonExporter,
    ParquetExporter,
)
from nexusai.infrastructure.export.sanitize import neutralise


class TestCsvExport:
    def test_produces_header_and_rows(self, dataset: ProcessedDataset, out_dir: Path) -> None:
        manifest = CsvExporter(out_dir).export(dataset, "out.csv")
        rows = list(csv.reader(Path(manifest.artifact.locator).read_text().splitlines()))
        assert rows[0][0] == "name"
        assert manifest.record_count == len(dataset.records)

    def test_preserves_source_provenance_column(
        self, dataset: ProcessedDataset, out_dir: Path
    ) -> None:
        CsvExporter(out_dir).export(dataset, "out.csv")
        text = (out_dir / "out.csv").read_text()
        assert "_source_uri" in text
        assert "https://shop/p1" in text

    def test_manifest_carries_hash_and_size(self, dataset: ProcessedDataset, out_dir: Path) -> None:
        manifest = CsvExporter(out_dir).export(dataset, "out.csv")
        assert manifest.content_hash.startswith("sha256:")
        assert manifest.size_bytes > 0


class TestFormulaInjection:
    def test_neutralise_prefixes_dangerous_values(self) -> None:
        assert neutralise("=1+1").startswith("'")
        assert neutralise("@cmd").startswith("'")
        assert neutralise("safe") == "safe"

    def test_csv_export_neutralises_formulas(self, out_dir: Path) -> None:
        dataset = type(make_dataset())(records=[make_record("p1", "=SUM(A1:A2)", 1, "https://x/1")])
        CsvExporter(out_dir).export(dataset, "out.csv")
        assert "'=SUM(A1:A2)" in (out_dir / "out.csv").read_text()


class TestJsonExport:
    def test_json_is_deterministic(self, dataset: ProcessedDataset, out_dir: Path) -> None:
        first = JsonExporter(out_dir).export(dataset, "a.json")
        second = JsonExporter(out_dir).export(dataset, "b.json")
        assert first.content_hash == second.content_hash

    def test_json_preserves_nested_values(self, out_dir: Path) -> None:
        dataset = type(make_dataset())(records=[make_record("p1", "x", [1, 2, 3], "https://x/1")])
        JsonExporter(out_dir).export(dataset, "a.json")
        payload = json.loads((out_dir / "a.json").read_text())
        assert payload[0]["fields"]["price"] == [1, 2, 3]


class TestNdjsonExport:
    def test_one_json_object_per_line(self, dataset: ProcessedDataset, out_dir: Path) -> None:
        NdjsonExporter(out_dir).export(dataset, "a.ndjson")
        lines = (out_dir / "a.ndjson").read_text().strip().splitlines()
        assert len(lines) == len(dataset.records)
        assert all(json.loads(line) for line in lines)


class TestExcelExport:
    def test_writes_summary_worksheets(self, dataset: ProcessedDataset, out_dir: Path) -> None:
        pytest.importorskip("openpyxl")
        import openpyxl

        ExcelExporter(out_dir).export(dataset, "a.xlsx")
        workbook = openpyxl.load_workbook(out_dir / "a.xlsx")
        assert {"Dataset", "Metadata", "Validation", "Quality"} <= set(workbook.sheetnames)

    def test_row_limit_raises_rather_than_truncates(
        self, out_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pytest.importorskip("openpyxl")
        from nexusai.infrastructure.export import excel_exporter

        monkeypatch.setattr(excel_exporter, "_MAX_ROWS", 2)
        dataset = make_dataset(count=5)
        with pytest.raises(ExportError):
            ExcelExporter(out_dir).export(dataset, "a.xlsx")


class TestParquetExport:
    def test_writes_typed_columns(self, dataset: ProcessedDataset, out_dir: Path) -> None:
        pytest.importorskip("pyarrow")
        import pyarrow.parquet as pq

        manifest = ParquetExporter(out_dir).export(dataset, "a.parquet")
        table = pq.read_table(manifest.artifact.locator)
        assert "name" in table.column_names
        assert "_source_uri" in table.column_names


class TestAtomicWrites:
    def test_failed_export_leaves_no_final_file(self, out_dir: Path) -> None:
        class Boom(JsonExporter):
            def export(
                self,
                dataset: ProcessedDataset,
                destination: str,
                *,
                version: object = None,
            ) -> ExportManifest:
                from nexusai.infrastructure.export.writer import atomic_output

                with atomic_output(self._base, destination):
                    raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            Boom(out_dir).export(make_dataset(), "a.json")
        assert not (out_dir / "a.json").exists()
        assert not list(out_dir.glob(".*tmp"))

    def test_export_rejects_path_traversal(self, dataset: ProcessedDataset, out_dir: Path) -> None:
        from nexusai.domain.errors.exceptions import StorageError

        with pytest.raises(StorageError):
            JsonExporter(out_dir).export(dataset, "../escape.json")
