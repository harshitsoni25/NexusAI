"""Deterministic, fixture-based benchmark scenarios.

Each scenario exercises one part of the pipeline against an in-memory fixture, so
it is reproducible and needs no network: extraction over fixed HTML, processing a
fixed set of extractions, persisting to an in-memory SQLite database, exporting to
a temporary directory, rendering a report, and an end-to-end combination. The
sizes scale the record count, so throughput can be read at small, medium and large
workloads.

What is deliberately *not* here is a browser scenario. Driving a real browser needs
a downloaded browser binary and is inherently non-deterministic and network-bound,
so it is reported as NOT VERIFIED rather than faked (see the CLI benchmark output).
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path

from nexusai.application.downstream import (
    DatasetPersistenceService,
    ReportAssembler,
)
from nexusai.domain.model.extraction import (
    ExtractedValue,
    ExtractionMethod,
    ExtractionResult,
    FieldProvenance,
)
from nexusai.domain.model.processing import (
    ProcessedDataset,
    ProcessedField,
    ProcessedRecord,
)
from nexusai.domain.provenance.source import SourceReference
from nexusai.infrastructure.export import CsvExporter, JsonExporter
from nexusai.infrastructure.persistence import (
    SqlAlchemyDatasetVersionStore,
    create_session_factory,
    create_sqlite_engine,
    initialise_schema,
)
from nexusai.infrastructure.reporting import HtmlReportRenderer

_PROVENANCE = FieldProvenance(method=ExtractionMethod.CSS)
_SOURCE = SourceReference(
    uri="https://benchmark.local/", retrieved_at=datetime(2025, 1, 1, tzinfo=UTC), method="http-get"
)


def _html(size: int) -> bytes:
    rows = "".join(
        f'<div class="product"><span class="name">Item {i}</span>'
        f'<span class="price">{i}.99</span></div>'
        for i in range(size)
    )
    return f"<html><body>{rows}</body></html>".encode()


def _extractions(size: int) -> list[ExtractionResult]:
    return [
        ExtractionResult(
            fields={
                "name": ExtractedValue(value=f"Item {i}", provenance=_PROVENANCE),
                "price": ExtractedValue(value=f"{i}.99", provenance=_PROVENANCE),
            }
        )
        for i in range(size)
    ]


def _dataset(size: int) -> ProcessedDataset:
    records = [
        ProcessedRecord(
            identity=f"r{i}",
            raw=ExtractionResult(),
            source=_SOURCE,
            fields={
                "name": ProcessedField(name="name", value=f"Item {i}", raw_value=f"Item {i}"),
                "price": ProcessedField(name="price", value=float(i), raw_value=f"{i}.99"),
            },
        )
        for i in range(size)
    ]
    return ProcessedDataset(records=records)


class ExtractionScenario:
    """Times CSS extraction over fixed HTML using lxml."""

    name = "extraction"

    def prepare(self, size: int) -> object:
        return _html(size)

    def execute(self, fixture: object) -> int:
        from lxml import html as lxml_html

        assert isinstance(fixture, bytes)
        tree = lxml_html.fromstring(fixture)
        count = 0
        for node in tree.cssselect("div.product"):
            name = node.cssselect(".name")
            price = node.cssselect(".price")
            _ = (name[0].text_content() if name else "", price[0].text_content() if price else "")
            count += 1
        return count


class ProcessingScenario:
    """Times assembling a processed dataset from extractions."""

    name = "processing"

    def prepare(self, size: int) -> object:
        return _extractions(size)

    def execute(self, fixture: object) -> int:
        assert isinstance(fixture, list)
        records = [
            ProcessedRecord(
                identity=f"r{i}",
                raw=extraction,
                source=_SOURCE,
                fields={
                    name: ProcessedField(
                        name=name, value=extraction.value(name), raw_value=extraction.value(name)
                    )
                    for name in extraction.fields
                },
            )
            for i, extraction in enumerate(fixture)
        ]
        dataset = ProcessedDataset(records=records)
        return len(dataset)


class PersistenceScenario:
    """Times persisting a dataset to an in-memory SQLite store."""

    name = "persistence"

    def prepare(self, size: int) -> object:
        return _dataset(size)

    def execute(self, fixture: object) -> int:
        assert isinstance(fixture, ProcessedDataset)
        engine = create_sqlite_engine()
        initialise_schema(engine)
        service = DatasetPersistenceService(
            SqlAlchemyDatasetVersionStore(create_session_factory(engine))
        )
        service.persist(fixture, "benchmark")
        return len(fixture)


class ExportScenario:
    """Times exporting a dataset to CSV and JSON."""

    name = "export"

    def prepare(self, size: int) -> object:
        directory = Path(tempfile.mkdtemp())
        return (_dataset(size), directory)

    def execute(self, fixture: object) -> int:
        assert isinstance(fixture, tuple)
        dataset, directory = fixture
        CsvExporter(directory).export(dataset, "bench.csv")
        JsonExporter(directory).export(dataset, "bench.json")
        return len(dataset)


class ReportingScenario:
    """Times assembling and rendering an HTML report."""

    name = "reporting"

    def prepare(self, size: int) -> object:
        directory = Path(tempfile.mkdtemp())
        return (_dataset(size), directory)

    def execute(self, fixture: object) -> int:
        assert isinstance(fixture, tuple)
        dataset, directory = fixture
        report = ReportAssembler().assemble(dataset)
        HtmlReportRenderer(directory).render(report, "bench.html")
        return len(dataset)


class EndToEndScenario:
    """Times extraction, processing, persistence, export and reporting together."""

    name = "end_to_end"

    def prepare(self, size: int) -> object:
        return _html(size)

    def execute(self, fixture: object) -> int:
        from lxml import html as lxml_html

        assert isinstance(fixture, bytes)
        tree = lxml_html.fromstring(fixture)
        extractions = []
        for node in tree.cssselect("div.product"):
            name = node.cssselect(".name")
            price = node.cssselect(".price")
            extractions.append(
                ExtractionResult(
                    fields={
                        "name": ExtractedValue(
                            value=name[0].text_content() if name else "", provenance=_PROVENANCE
                        ),
                        "price": ExtractedValue(
                            value=price[0].text_content() if price else "", provenance=_PROVENANCE
                        ),
                    }
                )
            )
        records = [
            ProcessedRecord(
                identity=f"r{i}",
                raw=extraction,
                source=_SOURCE,
                fields={
                    n: ProcessedField(
                        name=n, value=extraction.value(n), raw_value=extraction.value(n)
                    )
                    for n in extraction.fields
                },
            )
            for i, extraction in enumerate(extractions)
        ]
        dataset = ProcessedDataset(records=records)
        engine = create_sqlite_engine()
        initialise_schema(engine)
        DatasetPersistenceService(
            SqlAlchemyDatasetVersionStore(create_session_factory(engine))
        ).persist(dataset, "benchmark")
        directory = Path(tempfile.mkdtemp())
        CsvExporter(directory).export(dataset, "bench.csv")
        HtmlReportRenderer(directory).render(ReportAssembler().assemble(dataset), "bench.html")
        return len(dataset)


ALL_SCENARIOS = (
    ExtractionScenario(),
    ProcessingScenario(),
    PersistenceScenario(),
    ExportScenario(),
    ReportingScenario(),
    EndToEndScenario(),
)
