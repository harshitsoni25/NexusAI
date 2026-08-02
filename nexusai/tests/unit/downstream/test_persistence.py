"""Persistence: mapping, versioning, idempotency, transactions, schema lifecycle."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from downstream_builders import make_dataset
from nexusai.application.downstream import (
    DatasetPersistenceService,
    compute_content_hash,
)
from nexusai.domain.errors.exceptions import StorageError
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.infrastructure.persistence import (
    SUPPORTED_SCHEMA_VERSION,
    SqlAlchemyDatasetVersionStore,
    SqlAlchemyUnitOfWork,
    check_compatibility,
    create_session_factory,
    create_sqlite_engine,
    initialise_schema,
    read_schema_version,
)
from nexusai.infrastructure.persistence.mappers import (
    dataset_version_to_row,
    record_row_to_dict,
    record_to_row,
    row_to_dataset_version,
)
from nexusai.infrastructure.persistence.schema import SchemaVersionRow


class TestMapping:
    def test_dataset_version_round_trips_through_a_row(
        self, store: SqlAlchemyDatasetVersionStore
    ) -> None:
        service = DatasetPersistenceService(store)
        version = service.persist(make_dataset(), "cat", run_id="r1")
        row = dataset_version_to_row(version)
        restored = row_to_dataset_version(row)
        assert str(restored.dataset_id) == "cat"
        assert restored.content_hash == version.content_hash

    def test_record_payload_preserves_raw_values(self) -> None:
        record = make_dataset().records[1]
        row = record_to_row(record)
        payload = record_row_to_dict(row)
        fields = payload["fields"]
        assert isinstance(fields, dict)
        assert fields["price"]["raw_value"] == str(record.value("price"))


class TestVersioning:
    def test_versions_are_appended_not_overwritten(
        self, store: SqlAlchemyDatasetVersionStore
    ) -> None:
        service = DatasetPersistenceService(store)
        service.persist(make_dataset(count=2), "cat")
        service.persist(make_dataset(count=3), "cat")
        history = service.history("cat")
        assert [v.version for v in history] == [1, 2]

    def test_latest_returns_the_newest_version(self, store: SqlAlchemyDatasetVersionStore) -> None:
        service = DatasetPersistenceService(store)
        service.persist(make_dataset(count=2), "cat")
        service.persist(make_dataset(count=3), "cat")
        latest = store.latest("cat")
        assert latest is not None
        assert latest.version == 2

    def test_history_is_preserved_and_loadable(self, store: SqlAlchemyDatasetVersionStore) -> None:
        service = DatasetPersistenceService(store)
        service.persist(make_dataset(count=2), "cat")
        service.persist(make_dataset(count=4), "cat")
        first = service.load("cat", 1)
        assert first is not None
        assert first.version.record_count == 2


class TestIdempotency:
    def test_identical_content_returns_the_same_version(
        self, store: SqlAlchemyDatasetVersionStore
    ) -> None:
        service = DatasetPersistenceService(store)
        first = service.persist(make_dataset(count=2), "cat", run_id="r1")
        second = service.persist(make_dataset(count=2), "cat", run_id="r2")
        assert first.version == second.version == 1
        assert len(service.history("cat")) == 1

    def test_content_hash_is_order_independent(self) -> None:
        forward = make_dataset(count=3)
        reversed_records = type(forward)(
            records=list(reversed(forward.records)), context=forward.context
        )
        assert compute_content_hash(forward) == compute_content_hash(reversed_records)

    def test_content_hash_changes_with_content(self) -> None:
        assert compute_content_hash(make_dataset(count=2)) != compute_content_hash(
            make_dataset(count=3)
        )


class TestTransactions:
    def test_commit_persists_work(self) -> None:
        engine = create_sqlite_engine()
        initialise_schema(engine)
        factory = create_session_factory(engine)
        with SqlAlchemyUnitOfWork(factory) as uow:
            uow.session.add(SchemaVersionRow(version=99, label="temp"))
        with SqlAlchemyUnitOfWork(factory) as uow:
            rows = uow.session.query(SchemaVersionRow).count()
        assert rows == 2

    def test_rollback_on_exception_discards_work(self) -> None:
        engine = create_sqlite_engine()
        initialise_schema(engine)
        factory = create_session_factory(engine)
        with pytest.raises(RuntimeError), SqlAlchemyUnitOfWork(factory) as uow:
            uow.session.add(SchemaVersionRow(version=99, label="temp"))
            raise RuntimeError("boom")
        with SqlAlchemyUnitOfWork(factory) as uow:
            assert uow.session.query(SchemaVersionRow).count() == 1

    def test_session_outside_transaction_raises(self) -> None:
        factory = create_session_factory(create_sqlite_engine())
        with pytest.raises(StorageError):
            _ = SqlAlchemyUnitOfWork(factory).session


class TestConstraints:
    def test_duplicate_content_hash_is_rejected_at_the_database(
        self, store: SqlAlchemyDatasetVersionStore, dataset: ProcessedDataset
    ) -> None:
        from nexusai.domain.model.persistence import (
            DatasetId,
            DatasetVersion,
            StoredDataset,
        )

        stored = StoredDataset(
            version=DatasetVersion(dataset_id=DatasetId.of("cat"), version=0, content_hash="dup")
        )
        store.save(dataset, stored)
        with pytest.raises(StorageError):
            store.save(dataset, stored)


class TestSchemaLifecycle:
    def test_schema_version_is_stamped_on_init(self) -> None:
        engine = create_sqlite_engine()
        initialise_schema(engine)
        stored = read_schema_version(engine)
        assert stored is not None
        assert stored.version == SUPPORTED_SCHEMA_VERSION

    def test_compatible_schema_passes(self) -> None:
        engine = create_sqlite_engine()
        initialise_schema(engine)
        check_compatibility(engine)

    def test_newer_schema_is_refused(self) -> None:
        engine = create_sqlite_engine()
        initialise_schema(engine, version=99)
        with pytest.raises(StorageError):
            check_compatibility(engine, supported=1)

    def test_foreign_keys_are_enforced(self) -> None:
        engine = create_sqlite_engine()
        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1


class TestRetrieval:
    def test_get_returns_stored_sources(self, store: SqlAlchemyDatasetVersionStore) -> None:
        service = DatasetPersistenceService(store)
        service.persist(make_dataset(count=2), "cat", run_id="r1")
        loaded = store.get("cat", 1)
        assert loaded is not None
        assert any("shop" in source.uri for source in loaded.sources)

    def test_get_absent_version_returns_none(self, store: SqlAlchemyDatasetVersionStore) -> None:
        assert store.get("cat", 99) is None

    def test_iterate_records_yields_stored_payloads(
        self, store: SqlAlchemyDatasetVersionStore
    ) -> None:
        service = DatasetPersistenceService(store)
        service.persist(make_dataset(count=3), "cat")
        records = list(store.iterate_records("cat", 1))
        assert len(records) == 3
        assert all("fields" in record for record in records)  # dict[str, object]

    def test_iterate_records_of_absent_version_is_empty(
        self, store: SqlAlchemyDatasetVersionStore
    ) -> None:
        assert list(store.iterate_records("cat", 99)) == []

    def test_find_by_hash_returns_none_when_absent(
        self, store: SqlAlchemyDatasetVersionStore
    ) -> None:
        assert store.find_by_hash("cat", "sha256:nope") is None
