"""SQLAlchemy repositories implementing the persistence ports.

The dataset store implements :class:`DatasetVersionStore` and is the only place
that knows how a dataset version becomes rows. It returns domain value objects,
never ORM instances, so the SQLAlchemy session stays behind the boundary. Saving
allocates the next version for a dataset and persists the version together with
its records, issues, quality measurements and sources in one transaction, so a
version is never stored without the provenance and results that describe it.

Versioning is append-only: :meth:`save` computes the next version number and the
unique constraints on ``(dataset_id, version)`` and ``(dataset_id, content_hash)``
make overwriting or duplicating a version a database error rather than a silent
corruption, which is the backstop behind the application layer's idempotency
check.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from nexusai.domain.errors.exceptions import StorageError
from nexusai.domain.model.persistence import DatasetVersion, StoredDataset
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.infrastructure.persistence.mappers import (
    dataset_measurement_rows,
    dataset_version_to_row,
    issue_to_row,
    record_row_to_dict,
    record_to_row,
    row_to_dataset_version,
    source_to_row,
)
from nexusai.infrastructure.persistence.schema import DatasetVersionRow, RecordRow


class SqlAlchemyDatasetVersionStore:
    """Persists and retrieves versioned datasets in the metadata store."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, dataset: ProcessedDataset, stored: StoredDataset) -> DatasetVersion:
        """Persist a new version of a dataset atomically and return its metadata.

        The ``stored.version`` carries the intended metadata; the version number
        on it is ignored and the next number is allocated here, so a caller
        cannot accidentally overwrite an existing version.

        Raises:
            StorageError: If a version with the same content hash already exists,
                or the write violates a uniqueness constraint.
        """
        with self._session_factory() as session:
            next_version = self._next_version(session, str(stored.version.dataset_id))
            row = dataset_version_to_row(stored.version)
            row.version = next_version
            row.records = [record_to_row(record) for record in dataset.records]
            row.issues = [issue_to_row(issue) for issue in _context_issues(dataset)]
            row.measurements = dataset_measurement_rows(dataset)
            row.sources = [source_to_row(source) for source in stored.sources]
            session.add(row)
            try:
                session.commit()
            except Exception as exc:
                session.rollback()
                raise StorageError(
                    "Failed to persist dataset version",
                    dataset_id=str(stored.version.dataset_id),
                ) from exc
            return row_to_dataset_version(row)

    def get(self, dataset_id: str, version: int) -> StoredDataset | None:
        """Return a specific stored version, or ``None`` if absent."""
        with self._session_factory() as session:
            row = self._row(session, dataset_id, version)
            if row is None:
                return None
            from nexusai.infrastructure.persistence.mappers import row_to_source

            return StoredDataset(
                version=row_to_dataset_version(row),
                sources=[row_to_source(source) for source in row.sources],
            )

    def latest(self, dataset_id: str) -> DatasetVersion | None:
        """Return the most recent version's metadata, or ``None``."""
        with self._session_factory() as session:
            row = session.scalar(
                select(DatasetVersionRow)
                .where(DatasetVersionRow.dataset_id == dataset_id)
                .order_by(DatasetVersionRow.version.desc())
                .limit(1)
            )
            return row_to_dataset_version(row) if row is not None else None

    def versions(self, dataset_id: str) -> Sequence[DatasetVersion]:
        """Return every stored version's metadata, oldest first."""
        with self._session_factory() as session:
            rows = session.scalars(
                select(DatasetVersionRow)
                .where(DatasetVersionRow.dataset_id == dataset_id)
                .order_by(DatasetVersionRow.version.asc())
            ).all()
            return [row_to_dataset_version(row) for row in rows]

    def find_by_hash(self, dataset_id: str, content_hash: str) -> DatasetVersion | None:
        """Return an existing version with this content hash, for idempotency."""
        with self._session_factory() as session:
            row = session.scalar(
                select(DatasetVersionRow).where(
                    DatasetVersionRow.dataset_id == dataset_id,
                    DatasetVersionRow.content_hash == content_hash,
                )
            )
            return row_to_dataset_version(row) if row is not None else None

    def iterate_records(self, dataset_id: str, version: int) -> Iterator[dict[str, object]]:
        """Yield the stored records of a version, one at a time."""
        with self._session_factory() as session:
            parent = self._row(session, dataset_id, version)
            if parent is None:
                return
            record_rows = session.scalars(
                select(RecordRow).where(RecordRow.dataset_pk == parent.id)
            )
            for record_row in record_rows:
                yield record_row_to_dict(record_row)

    def _next_version(self, session: Session, dataset_id: str) -> int:
        highest = session.scalar(
            select(func.max(DatasetVersionRow.version)).where(
                DatasetVersionRow.dataset_id == dataset_id
            )
        )
        return (highest or 0) + 1

    def _row(self, session: Session, dataset_id: str, version: int) -> DatasetVersionRow | None:
        return session.scalar(
            select(DatasetVersionRow).where(
                DatasetVersionRow.dataset_id == dataset_id,
                DatasetVersionRow.version == version,
            )
        )


def _context_issues(dataset: ProcessedDataset) -> list:  # type: ignore[type-arg]
    if dataset.context is None:
        return []
    return list(dataset.context.validation_summary.issues)


def now() -> datetime:
    """Return the current UTC time (indirection kept for testability)."""
    from datetime import UTC

    return datetime.now(UTC)
