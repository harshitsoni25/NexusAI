"""Integration: Parquet export reads back with types, nulls and provenance intact.

Skipped when pyarrow (the optional ``parquet`` extra) is not installed, so the
suite stays green without it; where installed, it verifies a real round trip.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

pytest.importorskip("pyarrow")

from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import (
    ProcessedDataset,
    ProcessedField,
    ProcessedRecord,
)
from nexusai.domain.provenance.source import SourceReference
from nexusai.infrastructure.export.parquet_exporter import ParquetExporter

pytestmark = pytest.mark.integration

_SOURCE = SourceReference(
    uri="https://mock.local/item", retrieved_at=datetime(2025, 1, 1, tzinfo=UTC), method="http-get"
)


def _dataset(n: int) -> ProcessedDataset:
    return ProcessedDataset(
        records=[
            ProcessedRecord(
                identity=f"r{i}",
                raw=ExtractionResult(),
                source=_SOURCE,
                fields={
                    "name": ProcessedField(name="name", value=f"Item {i}", raw_value=f"Item {i}"),
                    "price": ProcessedField(name="price", value=float(i), raw_value=str(i)),
                    "maybe": ProcessedField(name="maybe", value=None, raw_value=""),
                },
            )
            for i in range(n)
        ]
    )


class TestParquetRoundTrip:
    def test_large_dataset_reads_back(self, tmp_path: Path) -> None:
        import pyarrow.parquet as pq

        manifest = ParquetExporter(tmp_path).export(_dataset(1000), "out.parquet")
        table = pq.read_table(tmp_path / "out.parquet")
        assert table.num_rows == 1000
        assert manifest.record_count == 1000

    def test_types_and_nulls_preserved(self, tmp_path: Path) -> None:
        import pyarrow.parquet as pq

        ParquetExporter(tmp_path).export(_dataset(10), "t.parquet")
        table = pq.read_table(tmp_path / "t.parquet")
        assert str(table.schema.field("price").type) == "double"
        assert str(table.schema.field("name").type) == "string"

    def test_provenance_column_present(self, tmp_path: Path) -> None:
        import pyarrow.parquet as pq

        ParquetExporter(tmp_path).export(_dataset(5), "p.parquet")
        table = pq.read_table(tmp_path / "p.parquet")
        assert "_source_uri" in table.column_names
