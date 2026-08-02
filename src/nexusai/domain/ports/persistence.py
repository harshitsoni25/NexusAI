"""Persistence contracts.

Repositories express the domain's persistence *intent* without knowing how it is
satisfied. The domain says "I need to store and retrieve these by identity"; an
infrastructure adapter satisfies that with SQLite, a file, or anything else, and
the domain neither knows nor cares which (ADR-0007 keeps the operational and
dataset stores behind two independent instances of these contracts).

Read and write are separated so that a component which only reads cannot
accidentally acquire the ability to write, and so that a read-only replica is a
legitimate implementation of the read side alone.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)
ID_contra = TypeVar("ID_contra", contravariant=True)


@runtime_checkable
class ReadableRepository(Protocol[T_co, ID_contra]):
    """Read access to persisted entities of one type."""

    def get(self, identity: ID_contra) -> T_co | None:
        """Return the entity with ``identity``, or ``None`` if absent."""
        ...

    def exists(self, identity: ID_contra) -> bool:
        """Whether an entity with ``identity`` is stored."""
        ...

    def iterate(self) -> Iterator[T_co]:
        """Yield stored entities one at a time.

        Iteration rather than a returned list is deliberate: the dataset store
        may hold far more than fits in memory, and streaming is what keeps memory
        a function of concurrency rather than dataset size.
        """
        ...

    def count(self) -> int:
        """Return how many entities are stored."""
        ...


@runtime_checkable
class WritableRepository(Protocol[T_contra, ID_contra]):
    """Write access to persisted entities of one type."""

    def add(self, entity: T_contra) -> None:
        """Persist a new entity."""
        ...

    def add_many(self, entities: Sequence[T_contra]) -> None:
        """Persist several entities.

        A distinct method rather than a loop over :meth:`add` so that an adapter
        can batch the write, which for most stores is dramatically cheaper than
        one round trip per entity.
        """
        ...

    def remove(self, identity: ID_contra) -> None:
        """Remove the entity with ``identity``. Absent identity is a no-op."""
        ...


@runtime_checkable
class Repository(
    ReadableRepository[T, ID_contra],
    WritableRepository[T, ID_contra],
    Protocol[T, ID_contra],
):
    """Combined read and write access to persisted entities of one type."""


@runtime_checkable
class UnitOfWork(Protocol):
    """A transactional boundary over one or more repositories.

    Used as a context manager. Work performed inside the block is committed on
    a clean exit and rolled back if an exception propagates, so a multi-write
    operation is atomic: either every write lands or none does. This is what lets
    records and their provenance be persisted in the same transaction (ADR-0008),
    so a record can never end up stored without its origin.
    """

    def __enter__(self) -> UnitOfWork:
        """Begin a transaction."""
        ...

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool | None:
        """Commit on a clean exit, roll back if an exception is propagating."""
        ...

    def commit(self) -> None:
        """Persist all work performed in this transaction."""
        ...

    def rollback(self) -> None:
        """Discard all work performed in this transaction."""
        ...
