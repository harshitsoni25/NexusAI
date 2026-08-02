"""Application service for persisting dataset versions.

Coordinates the persistence port with versioning and idempotency. Its job is to
answer "persist this processed dataset as a version of this dataset" while never
overwriting history and never duplicating an identical version. It computes a
content hash for the dataset, asks the store whether that hash is already present,
and if so returns the existing version untouched -- so a retry, resume or repeated
call is safe. Otherwise it appends a new version through the store, which
allocates the next version number.

The content hash is the idempotency key: identical processed content yields the
same hash and therefore the same version, while any change yields a new one.
"""

from __future__ import annotations

import hashlib
import json

from nexusai.domain.model.persistence import (
    DatasetId,
    DatasetVersion,
    StoredDataset,
)
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.domain.ports.storage import DatasetVersionStore


class DatasetPersistenceService:
    """Persists processed datasets as versions, idempotently."""

    def __init__(self, store: DatasetVersionStore) -> None:
        self._store = store

    def persist(
        self, dataset: ProcessedDataset, dataset_id: str, *, run_id: str | None = None
    ) -> DatasetVersion:
        """Persist ``dataset`` as a version of ``dataset_id`` and return it.

        If a version with identical content already exists, that version is
        returned and nothing new is written.
        """
        content_hash = compute_content_hash(dataset)
        existing = self._store.find_by_hash(dataset_id, content_hash)
        if existing is not None:
            return existing

        context = dataset.context
        stored = StoredDataset(
            version=DatasetVersion(
                dataset_id=DatasetId.of(dataset_id),
                version=0,
                run_id=run_id,
                processed_at=context.processed_at if context else None,
                content_hash=content_hash,
                record_count=len(dataset.records),
                quality_grade=context.quality_grade.value if context else None,
                configuration_ref=context.rule_version if context else None,
                source_count=self._source_count(dataset),
            ),
            sources=tuple(context.sources) if context else (),
        )
        return self._store.save(dataset, stored)

    def history(self, dataset_id: str) -> list[DatasetVersion]:
        """Return every persisted version of ``dataset_id``, oldest first."""
        return list(self._store.versions(dataset_id))

    def load(self, dataset_id: str, version: int) -> StoredDataset | None:
        """Load a specific stored version."""
        return self._store.get(dataset_id, version)

    def _source_count(self, dataset: ProcessedDataset) -> int:
        if dataset.context is not None and dataset.context.sources:
            return len(dataset.context.sources)
        return len({r.source.uri for r in dataset.records if r.source is not None})


def compute_content_hash(dataset: ProcessedDataset) -> str:
    """Return a deterministic content hash of a dataset's records.

    The hash covers each record's identity and processed values in a canonical,
    sorted JSON form, so identical content always hashes the same regardless of
    record ordering, and any change to the data changes the hash.
    """
    digest = hashlib.sha256()
    rows = sorted(
        json.dumps(
            {
                "identity": record.identity,
                "fields": {name: field.value for name, field in record.fields.items()},
            },
            sort_keys=True,
            default=str,
        )
        for record in dataset.records
    )
    for row in rows:
        digest.update(row.encode("utf-8"))
        digest.update(b"\n")
    return f"sha256:{digest.hexdigest()}"
