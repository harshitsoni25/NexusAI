"""Persistence of export and report manifests and artefact metadata.

Every export, report and stored artefact leaves an auditable trail: this
repository writes their manifests to the metadata store and reads them back as
domain value objects. It is separate from the dataset store because it records
*outputs* rather than versions, but shares the same session factory and boundary
discipline -- rows in, values out.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from nexusai.domain.model.persistence import (
    ArtifactMetadata,
    ArtifactType,
    ExportManifest,
    OutcomeStatus,
    ReportManifest,
)
from nexusai.domain.provenance.source import ArtifactReference
from nexusai.infrastructure.persistence.schema import (
    ArtifactRow,
    ExportRow,
    ReportRow,
)


class SqlAlchemyManifestStore:
    """Persists and retrieves export, report and artefact manifests."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_export(self, manifest: ExportManifest) -> None:
        """Persist an export manifest."""
        with self._session_factory() as session:
            session.add(
                ExportRow(
                    export_id=manifest.export_id,
                    dataset_id=manifest.dataset_id,
                    dataset_version=manifest.dataset_version,
                    export_format=manifest.export_format,
                    locator=manifest.artifact.locator,
                    record_count=manifest.record_count,
                    size_bytes=manifest.size_bytes,
                    content_hash=manifest.content_hash,
                    created_at=manifest.created_at,
                    status=manifest.status.value,
                )
            )
            session.commit()

    def record_report(self, manifest: ReportManifest) -> None:
        """Persist a report manifest."""
        with self._session_factory() as session:
            session.add(
                ReportRow(
                    report_id=manifest.report_id,
                    dataset_id=manifest.dataset_id,
                    dataset_version=manifest.dataset_version,
                    report_format=manifest.report_format,
                    locator=manifest.artifact.locator,
                    size_bytes=manifest.size_bytes,
                    content_hash=manifest.content_hash,
                    created_at=manifest.created_at,
                    status=manifest.status.value,
                )
            )
            session.commit()

    def record_artifact(self, metadata: ArtifactMetadata) -> None:
        """Persist artefact metadata."""
        with self._session_factory() as session:
            session.add(
                ArtifactRow(
                    artifact_id=metadata.artifact_id,
                    artifact_type=metadata.artifact_type.value,
                    locator=metadata.locator,
                    media_type=metadata.media_type,
                    size_bytes=metadata.size_bytes,
                    content_hash=metadata.content_hash,
                    created_at=metadata.created_at,
                    dataset_id=metadata.dataset_id,
                    dataset_version=metadata.dataset_version,
                    run_ref=metadata.run_ref,
                )
            )
            session.commit()

    def exports_for(self, dataset_id: str) -> Sequence[ExportManifest]:
        """Return every export manifest for a dataset."""
        with self._session_factory() as session:
            rows = session.scalars(
                select(ExportRow).where(ExportRow.dataset_id == dataset_id)
            ).all()
            return [self._export_from_row(row) for row in rows]

    def artifacts_for(self, dataset_id: str) -> Sequence[ArtifactMetadata]:
        """Return every artefact metadata for a dataset."""
        with self._session_factory() as session:
            rows = session.scalars(
                select(ArtifactRow).where(ArtifactRow.dataset_id == dataset_id)
            ).all()
            return [self._artifact_from_row(row) for row in rows]

    def _export_from_row(self, row: ExportRow) -> ExportManifest:
        return ExportManifest(
            export_id=row.export_id,
            dataset_id=row.dataset_id,
            dataset_version=row.dataset_version,
            export_format=row.export_format,
            artifact=ArtifactReference(
                locator=row.locator,
                media_type="application/octet-stream",
                size_bytes=row.size_bytes,
            ),
            record_count=row.record_count,
            size_bytes=row.size_bytes,
            content_hash=row.content_hash,
            created_at=row.created_at,
            status=OutcomeStatus(row.status),
        )

    def _artifact_from_row(self, row: ArtifactRow) -> ArtifactMetadata:
        return ArtifactMetadata(
            artifact_id=row.artifact_id,
            artifact_type=ArtifactType(row.artifact_type),
            locator=row.locator,
            media_type=row.media_type,
            size_bytes=row.size_bytes,
            content_hash=row.content_hash,
            created_at=row.created_at,
            dataset_id=row.dataset_id,
            dataset_version=row.dataset_version,
            run_ref=row.run_ref,
        )
