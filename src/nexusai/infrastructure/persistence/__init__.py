"""Relational persistence for framework metadata, backed by SQLAlchemy.

SQLAlchemy lives here and nowhere else. The engine, session, ORM schema, mappers,
unit of work and repositories together satisfy the domain's backend-independent
persistence ports; the application and domain see only value objects.
"""

from __future__ import annotations

from nexusai.infrastructure.persistence.application_stores import (
    SqlAlchemyCheckpointStore,
    SqlAlchemyJobStore,
    SqlAlchemyScheduleStore,
)
from nexusai.infrastructure.persistence.engine import (
    SUPPORTED_SCHEMA_VERSION,
    check_compatibility,
    create_session_factory,
    create_sqlite_engine,
    initialise_schema,
    read_schema_version,
)
from nexusai.infrastructure.persistence.manifests import SqlAlchemyManifestStore
from nexusai.infrastructure.persistence.repository import (
    SqlAlchemyDatasetVersionStore,
)
from nexusai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork

__all__ = [
    "SUPPORTED_SCHEMA_VERSION",
    "SqlAlchemyCheckpointStore",
    "SqlAlchemyDatasetVersionStore",
    "SqlAlchemyJobStore",
    "SqlAlchemyManifestStore",
    "SqlAlchemyScheduleStore",
    "SqlAlchemyUnitOfWork",
    "check_compatibility",
    "create_session_factory",
    "create_sqlite_engine",
    "initialise_schema",
    "read_schema_version",
]
