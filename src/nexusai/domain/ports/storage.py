"""Backend-independent contracts for the downstream data lifecycle.

Four ports cover Phase 6's pluggable backends. A :class:`DatasetVersionStore`
persists and retrieves dataset versions and never reveals how -- SQLite today, a
different database tomorrow. An :class:`ArtifactStore` holds artefact bytes with
integrity, behind a locator that could be a path or an object-store URL. A
:class:`DatasetExporter` turns a processed dataset into an export artefact, and a
:class:`ReportRenderer` turns a report model into a report artefact.

None of these expose an infrastructure type. A repository returns domain value
objects, an exporter returns a domain manifest; the SQLAlchemy session, the
openpyxl workbook and the reportlab canvas stay behind the boundary (the
architecture layer test enforces this). Read and write stay separated on the
dataset store so a read-only consumer cannot acquire the ability to write.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from nexusai.domain.model.persistence import (
    ArtifactMetadata,
    ArtifactType,
    DatasetVersion,
    ExportManifest,
    ReportManifest,
    StoredDataset,
)

if TYPE_CHECKING:
    from nexusai.domain.model.processing import ProcessedDataset
    from nexusai.domain.model.report import Report


@runtime_checkable
class DatasetVersionStore(Protocol):
    """Persists and retrieves versioned datasets, backend-independently.

    Versions are append-only: :meth:`save` allocates the next version for a
    dataset and never overwrites an existing one, so history is preserved. The
    store returns domain value objects, never rows.
    """

    def save(self, dataset: ProcessedDataset, stored: StoredDataset) -> DatasetVersion:
        """Persist a new version of a dataset and return its version metadata."""
        ...

    def get(self, dataset_id: str, version: int) -> StoredDataset | None:
        """Return a specific stored version, or ``None`` if absent."""
        ...

    def latest(self, dataset_id: str) -> DatasetVersion | None:
        """Return the most recent version's metadata, or ``None`` if none exist."""
        ...

    def versions(self, dataset_id: str) -> Sequence[DatasetVersion]:
        """Return every stored version's metadata, oldest first."""
        ...

    def find_by_hash(self, dataset_id: str, content_hash: str) -> DatasetVersion | None:
        """Return an existing version with this content hash, for idempotency."""
        ...

    def iterate_records(self, dataset_id: str, version: int) -> Iterator[dict[str, object]]:
        """Yield the stored records of a version, one at a time.

        Iteration rather than a list keeps memory a function of concurrency, not
        dataset size, matching the read repository contract.
        """
        ...


@runtime_checkable
class ArtifactStore(Protocol):
    """Stores artefact bytes with integrity, behind a backend-independent handle.

    Separate from the relational store (the master specification requires it) so
    that a future object-store backend can hold bytes remotely while metadata
    stays relational. Every stored artefact carries a cryptographic content hash,
    and :meth:`verify` re-reads and re-hashes to detect modification.
    """

    def put(
        self,
        name: str,
        data: bytes,
        media_type: str,
        *,
        artifact_type: ArtifactType,
        dataset_id: str | None = None,
        dataset_version: int | None = None,
        run_ref: str | None = None,
    ) -> ArtifactMetadata:
        """Store ``data`` and return its metadata, including a content hash."""
        ...

    def get(self, artifact_id: str) -> bytes:
        """Return the stored bytes of an artefact.

        Raises:
            StorageError: If the artefact is absent.
        """
        ...

    def metadata(self, artifact_id: str) -> ArtifactMetadata | None:
        """Return an artefact's metadata, or ``None`` if absent."""
        ...

    def verify(self, artifact_id: str) -> bool:
        """Re-read the artefact and confirm its bytes still match the hash."""
        ...


@runtime_checkable
class DatasetExporter(Protocol):
    """Turns a processed dataset into an export artefact.

    An exporter reads a dataset and writes a file; it never queries a database,
    re-runs validation or quality assessment, or modifies the dataset. It returns
    a manifest describing what it wrote.
    """

    @property
    def export_format(self) -> str:
        """The format name, such as ``csv`` or ``parquet``."""
        ...

    @property
    def media_type(self) -> str:
        """The MIME type of the produced artefact."""
        ...

    def export(
        self,
        dataset: ProcessedDataset,
        destination: str,
        *,
        version: DatasetVersion | None = None,
    ) -> ExportManifest:
        """Write ``dataset`` to ``destination`` and return the manifest.

        When ``version`` is given, the manifest is tied to that dataset version;
        otherwise a neutral placeholder identity is used, which the application
        layer may replace with the persisted identity.
        """
        ...


@runtime_checkable
class ReportRenderer(Protocol):
    """Turns a report model into a report artefact.

    A renderer consumes the stable :class:`~nexusai.domain.model.report.Report`
    and writes a presentation file. It never recalculates a Phase 5 result and
    never touches a database or ORM row.
    """

    @property
    def report_format(self) -> str:
        """The format name, such as ``html`` or ``pdf``."""
        ...

    @property
    def media_type(self) -> str:
        """The MIME type of the produced artefact."""
        ...

    def render(self, report: Report, destination: str) -> ReportManifest:
        """Write ``report`` to ``destination`` and return the manifest."""
        ...
