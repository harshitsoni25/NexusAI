"""Engine, session factory and schema lifecycle for the metadata store.

This module owns the only place SQLAlchemy's engine and session are created. It
turns a backend-independent database URL into a configured engine, enforces the
SQLite pragmas the schema relies on (foreign-key enforcement is off by default in
SQLite and the cascade deletes need it on), initialises the schema, and records
and checks the schema version.

Schema versioning is deliberately minimal and dependency-free: a single-row
``schema_version`` table, an initialise step that creates tables and stamps the
version, and a compatibility check that refuses a store written by a newer schema
than the code understands. That is the upgrade boundary a future migration tool
would hook into, without committing to one now.
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from nexusai.domain.errors.exceptions import StorageError
from nexusai.domain.model.persistence import SchemaVersion
from nexusai.infrastructure.persistence.schema import Base, SchemaVersionRow

SUPPORTED_SCHEMA_VERSION = 1


def create_sqlite_engine(url: str = "sqlite:///:memory:", *, echo: bool = False) -> Engine:
    """Create an engine for the metadata store with SQLite pragmas applied.

    Foreign-key enforcement is enabled per connection, because SQLite leaves it
    off by default and the schema's cascade deletes depend on it.

    Args:
        url: A SQLAlchemy database URL. Defaults to an in-memory database.
        echo: Whether to log SQL, for debugging.
    """
    engine = create_engine(url, echo=echo, future=True)

    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection: object, _record: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a session factory bound to ``engine``."""
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


def initialise_schema(engine: Engine, *, version: int = SUPPORTED_SCHEMA_VERSION) -> None:
    """Create all tables and stamp the schema version if not already present."""
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        existing = session.scalar(select(SchemaVersionRow).limit(1))
        if existing is None:
            session.add(SchemaVersionRow(version=version, label="initial"))
            session.commit()


def read_schema_version(engine: Engine) -> SchemaVersion | None:
    """Return the stored schema version, or ``None`` if uninitialised."""
    with Session(engine) as session:
        row = session.scalar(select(SchemaVersionRow).limit(1))
        if row is None:
            return None
        return SchemaVersion(version=row.version, label=row.label)


def check_compatibility(engine: Engine, *, supported: int = SUPPORTED_SCHEMA_VERSION) -> None:
    """Raise if the store's schema is newer than the code supports.

    Raises:
        StorageError: If the store was written by a newer schema version.
    """
    stored = read_schema_version(engine)
    if stored is None:
        return
    if not stored.is_compatible_with(supported):
        raise StorageError(
            "Metadata store schema is newer than this version of the framework",
            stored_version=stored.version,
            supported_version=supported,
        )
