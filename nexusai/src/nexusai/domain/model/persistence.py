"""Storage-independent models for the downstream data lifecycle.

These are the value objects that cross the persistence, export and reporting
boundaries. They are frozen dataclasses that know nothing of SQLAlchemy, SQLite
or the filesystem: a :class:`DatasetVersion` describes a persisted version, an
:class:`ArtifactMetadata` describes a stored artefact, and an
:class:`ExportManifest` or :class:`ReportManifest` describes an output that was
produced. Infrastructure maps these to and from its own representations at its
boundary; the domain never sees the mapping.

Identity and versioning are explicit here because the whole downstream lifecycle
turns on them: a dataset is identified stably, each processing run appends a new
version rather than overwriting one, and every artefact, export and report is
tied back to the dataset version it came from, so provenance survives to the end.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from nexusai.domain.provenance.source import ArtifactReference, SourceReference
from nexusai.shared.identifiers import Identifier
from nexusai.shared.types import JsonValue


class DatasetId(Identifier):
    """The stable identity of a logical dataset across all its versions."""


class OutcomeStatus(Enum):
    """The outcome of a downstream operation."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"


class ArtifactType(Enum):
    """The kind of artefact stored, for retention and reporting."""

    HTML_SNAPSHOT = "html-snapshot"
    DOM_SNAPSHOT = "dom-snapshot"
    SCREENSHOT = "screenshot"
    DOWNLOAD = "download"
    EXPORT = "export"
    REPORT = "report"
    DIFF = "diff"
    OTHER = "other"


@dataclass(frozen=True, slots=True, kw_only=True)
class SchemaVersion:
    """The version of the persistence schema, for compatibility checks.

    Attributes:
        version: A monotonically increasing integer. A store written by a newer
            schema than the running code understands is refused rather than
            silently misread.
        label: A human-readable description of the schema revision.
    """

    version: int
    label: str = ""

    def is_compatible_with(self, supported: int) -> bool:
        """Whether a store at this version can be read by code supporting ``supported``.

        Forward compatibility only: code understands its own version and older,
        never a version from the future.
        """
        return self.version <= supported


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetVersion:
    """Metadata describing one persisted version of a dataset.

    Attributes:
        dataset_id: The logical dataset this version belongs to.
        version: The version number, starting at one and incrementing per run.
        run_id: The processing run that produced this version, when known.
        processed_at: When the dataset was processed.
        content_hash: A hash of the dataset's content, used to detect an
            already-persisted version and make persistence idempotent.
        record_count: How many records the version holds.
        quality_grade: The dataset's quality grade letter, when assessed.
        configuration_ref: A reference to the configuration snapshot in effect.
        source_count: How many distinct sources contributed.
    """

    dataset_id: DatasetId
    version: int
    run_id: str | None = None
    processed_at: datetime | None = None
    content_hash: str = ""
    record_count: int = 0
    quality_grade: str | None = None
    configuration_ref: str | None = None
    source_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "dataset_id": str(self.dataset_id),
            "version": self.version,
            "run_id": self.run_id,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "content_hash": self.content_hash,
            "record_count": self.record_count,
            "quality_grade": self.quality_grade,
            "configuration_ref": self.configuration_ref,
            "source_count": self.source_count,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactMetadata:
    """Backend-independent metadata describing a stored artefact.

    The metadata is deliberately separate from the artefact bytes so that a
    future object-store backend can hold the bytes remotely while this metadata
    stays in the relational store, tying the artefact to its dataset version.

    Attributes:
        artifact_id: The stable identity of the artefact.
        artifact_type: What kind of artefact it is.
        locator: A backend-independent handle to the bytes -- a path today, a
            URL under a future object store.
        media_type: The artefact's MIME type.
        size_bytes: The artefact's size.
        content_hash: A cryptographic hash of the bytes, for integrity checks.
        created_at: When the artefact was stored.
        dataset_id: The dataset the artefact belongs to, when applicable.
        dataset_version: The dataset version, when applicable.
        run_ref: The run that produced the artefact, when applicable.
        integrity_verified: Whether the stored bytes last matched ``content_hash``.
    """

    artifact_id: str
    artifact_type: ArtifactType
    locator: str
    media_type: str
    size_bytes: int
    content_hash: str
    created_at: datetime
    dataset_id: str | None = None
    dataset_version: int | None = None
    run_ref: str | None = None
    integrity_verified: bool = True

    def to_reference(self) -> ArtifactReference:
        """Return the provenance reference for this artefact."""
        return ArtifactReference(
            locator=self.locator, media_type=self.media_type, size_bytes=self.size_bytes
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type.value,
            "locator": self.locator,
            "media_type": self.media_type,
            "size_bytes": self.size_bytes,
            "content_hash": self.content_hash,
            "created_at": self.created_at.isoformat(),
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "run_ref": self.run_ref,
            "integrity_verified": self.integrity_verified,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ExportManifest:
    """Structured metadata describing one export operation.

    Produced by every export, this is the record that makes an export
    reproducible and auditable: it ties the output artefact back to the dataset
    version, records the format and exporter version, and carries the size and
    content hash of what was written.
    """

    export_id: str
    dataset_id: str
    dataset_version: int
    export_format: str
    artifact: ArtifactReference
    record_count: int
    size_bytes: int
    content_hash: str
    created_at: datetime
    duration_seconds: float = 0.0
    status: OutcomeStatus = OutcomeStatus.SUCCESS
    exporter_version: str = ""
    run_ref: str | None = None
    attributes: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", dict(self.attributes))

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "export_id": self.export_id,
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "export_format": self.export_format,
            "artifact": self.artifact.to_dict(),
            "record_count": self.record_count,
            "size_bytes": self.size_bytes,
            "content_hash": self.content_hash,
            "created_at": self.created_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "status": self.status.value,
            "exporter_version": self.exporter_version,
            "run_ref": self.run_ref,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportManifest:
    """Structured metadata describing one generated report."""

    report_id: str
    dataset_id: str
    dataset_version: int
    report_format: str
    artifact: ArtifactReference
    size_bytes: int
    content_hash: str
    created_at: datetime
    status: OutcomeStatus = OutcomeStatus.SUCCESS
    generator_version: str = ""
    run_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "report_id": self.report_id,
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "report_format": self.report_format,
            "artifact": self.artifact.to_dict(),
            "size_bytes": self.size_bytes,
            "content_hash": self.content_hash,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "generator_version": self.generator_version,
            "run_ref": self.run_ref,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class StoredDataset:
    """A dataset version paired with the source references behind it.

    The unit the persistence service saves and loads. It keeps the version
    metadata and the provenance roots together, so a loaded dataset can always
    answer where its data came from.
    """

    version: DatasetVersion
    sources: Sequence[SourceReference] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "sources", tuple(self.sources))
