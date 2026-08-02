"""Export and manifest services, and failure propagation."""

from __future__ import annotations

from pathlib import Path

import pytest

from nexusai.application.downstream import ExportService
from nexusai.domain.errors.exceptions import ExportError
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.infrastructure.export import CsvExporter, JsonExporter
from nexusai.infrastructure.persistence import (
    SqlAlchemyDatasetVersionStore,
    SqlAlchemyManifestStore,
    create_session_factory,
    create_sqlite_engine,
    initialise_schema,
)


class TestExportService:
    def test_dispatches_to_registered_exporter(
        self, dataset: ProcessedDataset, out_dir: Path
    ) -> None:
        service = ExportService()
        service.register(CsvExporter(out_dir))
        service.register(JsonExporter(out_dir))
        manifest = service.export(dataset, "csv", "a.csv")
        assert manifest.export_format == "csv"
        assert service.formats() == ["csv", "json"]

    def test_unknown_format_raises(self, dataset: ProcessedDataset, out_dir: Path) -> None:
        with pytest.raises(ExportError):
            ExportService().export(dataset, "xml", "a.xml")

    def test_version_identity_flows_into_manifest(
        self, dataset: ProcessedDataset, out_dir: Path, store: SqlAlchemyDatasetVersionStore
    ) -> None:
        from nexusai.application.downstream import DatasetPersistenceService

        version = DatasetPersistenceService(store).persist(dataset, "cat")
        service = ExportService()
        service.register(JsonExporter(out_dir))
        manifest = service.export(dataset, "json", "a.json", version=version)
        assert manifest.dataset_id == "cat"
        assert manifest.dataset_version == 1


class TestManifestStore:
    def _store(self) -> SqlAlchemyManifestStore:
        engine = create_sqlite_engine()
        initialise_schema(engine)
        return SqlAlchemyManifestStore(create_session_factory(engine))

    def test_export_manifest_round_trips(self, dataset: ProcessedDataset, out_dir: Path) -> None:
        manifest = JsonExporter(out_dir).export(dataset, "a.json")
        store = self._store()
        store.record_export(manifest)
        stored = store.exports_for(manifest.dataset_id)
        assert len(stored) == 1
        assert stored[0].export_format == "json"

    def test_artifact_metadata_round_trips(self) -> None:
        from datetime import UTC, datetime

        from nexusai.domain.model.persistence import ArtifactMetadata, ArtifactType

        metadata = ArtifactMetadata(
            artifact_id="a1",
            artifact_type=ArtifactType.EXPORT,
            locator="/tmp/a",
            media_type="text/csv",
            size_bytes=10,
            content_hash="sha256:x",
            created_at=datetime.now(UTC),
            dataset_id="cat",
        )
        store = self._store()
        store.record_artifact(metadata)
        assert store.artifacts_for("cat")[0].artifact_id == "a1"


class TestFailurePropagation:
    def test_storage_failure_surfaces_as_storage_error(
        self, store: SqlAlchemyDatasetVersionStore, dataset: ProcessedDataset
    ) -> None:
        from nexusai.domain.errors.exceptions import StorageError
        from nexusai.domain.model.persistence import (
            DatasetId,
            DatasetVersion,
            StoredDataset,
        )

        stored = StoredDataset(
            version=DatasetVersion(dataset_id=DatasetId.of("c"), version=0, content_hash="h")
        )
        store.save(dataset, stored)
        with pytest.raises(StorageError):
            store.save(dataset, stored)


class TestReportManifestPersistence:
    def test_report_manifest_round_trips(self, dataset: ProcessedDataset, out_dir: Path) -> None:
        from nexusai.application.downstream import ReportAssembler
        from nexusai.domain.model.persistence import DatasetId, DatasetVersion
        from nexusai.infrastructure.reporting import JsonReportRenderer

        version = DatasetVersion(dataset_id=DatasetId.of("cat"), version=1)
        report = ReportAssembler().assemble(dataset, version=version)
        manifest = JsonReportRenderer(out_dir).render(report, "r.json")

        engine = create_sqlite_engine()
        initialise_schema(engine)
        store = SqlAlchemyManifestStore(create_session_factory(engine))
        store.record_report(manifest)  # should not raise
