"""Integration: datasets persist, version, and read back with integrity.

These exercise the persistence service over a real (in-memory) SQLite engine and
the SQLAlchemy version store together: a dataset persists as version 1, an
identical re-persist is idempotent (no new version), and a changed dataset appends
version 2. This is the data-integrity path — versioning and idempotency — verified
end to end rather than mocked.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nexusai.application.downstream import DatasetPersistenceService
from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import (
    ProcessedDataset,
    ProcessedField,
    ProcessedRecord,
)
from nexusai.domain.provenance.source import SourceReference
from nexusai.infrastructure.persistence import (
    SqlAlchemyDatasetVersionStore,
    create_session_factory,
    create_sqlite_engine,
    initialise_schema,
)

pytestmark = pytest.mark.integration

_SOURCE = SourceReference(
    uri="https://mock.local/", retrieved_at=datetime(2025, 1, 1, tzinfo=UTC), method="http-get"
)


def _dataset(value: str) -> ProcessedDataset:
    record = ProcessedRecord(
        identity="r0",
        raw=ExtractionResult(),
        source=_SOURCE,
        fields={"name": ProcessedField(name="name", value=value, raw_value=value)},
    )
    return ProcessedDataset(records=[record])


@pytest.fixture
def store() -> SqlAlchemyDatasetVersionStore:
    engine = create_sqlite_engine()
    initialise_schema(engine)
    return SqlAlchemyDatasetVersionStore(create_session_factory(engine))


class TestVersioning:
    def test_first_persist_creates_version_one(self, store: SqlAlchemyDatasetVersionStore) -> None:
        service = DatasetPersistenceService(store)
        version = service.persist(_dataset("a"), "ds")
        assert version.version == 1
        assert store.latest("ds") is not None

    def test_identical_persist_is_idempotent(self, store: SqlAlchemyDatasetVersionStore) -> None:
        service = DatasetPersistenceService(store)
        service.persist(_dataset("a"), "ds")
        service.persist(_dataset("a"), "ds")
        assert len(store.versions("ds")) == 1

    def test_changed_dataset_appends_version(self, store: SqlAlchemyDatasetVersionStore) -> None:
        service = DatasetPersistenceService(store)
        service.persist(_dataset("a"), "ds")
        second = service.persist(_dataset("b"), "ds")
        assert second.version == 2
        assert len(store.versions("ds")) == 2

    def test_stored_records_read_back(self, store: SqlAlchemyDatasetVersionStore) -> None:
        DatasetPersistenceService(store).persist(_dataset("hello"), "ds")
        latest = store.latest("ds")
        assert latest is not None
        stored = store.get("ds", latest.version)
        assert stored is not None
