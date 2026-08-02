"""SQLAlchemy declarative schema for the metadata store.

These ORM rows are infrastructure detail and never cross the persistence
boundary: the mapper layer converts them to and from domain value objects, so no
SQLAlchemy type is ever returned to the application or domain. The schema is
normalised rather than a bag of JSON blobs -- validation issues, quality
measurements and provenance are their own tables keyed to a dataset version --
so history can be queried without rehydrating whole payloads, while the record
payloads themselves are stored as JSON text because their shape is caller-defined.

A dataset version is the hub: every issue, measurement, source and record row
references it, and a version is never updated in place, which is how history is
preserved.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """The declarative base for every metadata table."""


class SchemaVersionRow(Base):
    """A single row recording the schema version the store was written with."""

    __tablename__ = "schema_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(255), default="")


class DatasetVersionRow(Base):
    """One persisted version of a dataset -- the hub of the schema."""

    __tablename__ = "dataset_version"
    __table_args__ = (
        UniqueConstraint("dataset_id", "version", name="uq_dataset_version"),
        UniqueConstraint("dataset_id", "content_hash", name="uq_dataset_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    quality_grade: Mapped[str | None] = mapped_column(String(2), nullable=True)
    configuration_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_count: Mapped[int] = mapped_column(Integer, default=0)

    records: Mapped[list[RecordRow]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    issues: Mapped[list[ValidationIssueRow]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    measurements: Mapped[list[QualityMeasurementRow]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    sources: Mapped[list[SourceRow]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class RecordRow(Base):
    """One processed record, its payload stored as JSON text."""

    __tablename__ = "record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_pk: Mapped[int] = mapped_column(
        ForeignKey("dataset_version.id", ondelete="CASCADE"), index=True
    )
    identity: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)

    dataset: Mapped[DatasetVersionRow] = relationship(back_populates="records")


class ValidationIssueRow(Base):
    """One validation issue from a dataset version's summary."""

    __tablename__ = "validation_issue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_pk: Mapped[int] = mapped_column(
        ForeignKey("dataset_version.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    dataset: Mapped[DatasetVersionRow] = relationship(back_populates="issues")


class QualityMeasurementRow(Base):
    """One quality dimension score from a dataset version."""

    __tablename__ = "quality_measurement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_pk: Mapped[int] = mapped_column(
        ForeignKey("dataset_version.id", ondelete="CASCADE"), index=True
    )
    dimension: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    dataset: Mapped[DatasetVersionRow] = relationship(back_populates="measurements")


class SourceRow(Base):
    """One source-provenance reference for a dataset version."""

    __tablename__ = "source_reference"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_pk: Mapped[int] = mapped_column(
        ForeignKey("dataset_version.id", ondelete="CASCADE"), index=True
    )
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    retrieved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    dataset: Mapped[DatasetVersionRow] = relationship(back_populates="sources")


class ArtifactRow(Base):
    """Metadata for one stored artefact."""

    __tablename__ = "artifact"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    locator: Mapped[str] = mapped_column(Text, nullable=False)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    dataset_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dataset_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    run_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ExportRow(Base):
    """An export manifest, persisted for auditing."""

    __tablename__ = "export_manifest"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    export_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    dataset_version: Mapped[int] = mapped_column(Integer, nullable=False)
    export_format: Mapped[str] = mapped_column(String(32), nullable=False)
    locator: Mapped[str] = mapped_column(Text, nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="success")


class ReportRow(Base):
    """A report manifest, persisted for auditing."""

    __tablename__ = "report_manifest"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    dataset_version: Mapped[int] = mapped_column(Integer, nullable=False)
    report_format: Mapped[str] = mapped_column(String(32), nullable=False)
    locator: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="success")
