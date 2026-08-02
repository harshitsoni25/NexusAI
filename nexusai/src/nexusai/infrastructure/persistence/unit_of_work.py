"""A SQLAlchemy-backed unit of work.

Implements the domain's :class:`~nexusai.domain.ports.persistence.UnitOfWork`
contract over a SQLAlchemy session. Used as a context manager, it commits on a
clean exit and rolls back if an exception propagates, so a logical operation --
saving a dataset version together with its records, issues, measurements and
sources -- is atomic: either all of it lands or none of it does. The session is
always closed, even on failure, so a failed operation never leaks a connection.
"""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

from nexusai.domain.errors.exceptions import StorageError


class SqlAlchemyUnitOfWork:
    """A transactional boundary over a single SQLAlchemy session."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

    @property
    def session(self) -> Session:
        """The active session.

        Raises:
            StorageError: If accessed outside an active transaction.
        """
        if self._session is None:
            raise StorageError("Unit of work is not active")
        return self._session

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        """Open a session and begin a transaction."""
        self._session = self._session_factory()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Commit on a clean exit, roll back on error, and always close.

        Returns ``None`` so a propagating exception is never suppressed: a failed
        transaction must surface to the caller, not be swallowed here.
        """
        try:
            if exc_type is not None:
                self.rollback()
            else:
                self.commit()
        finally:
            if self._session is not None:
                self._session.close()
                self._session = None

    def commit(self) -> None:
        """Persist all work performed in this transaction."""
        if self._session is not None:
            self._session.commit()

    def rollback(self) -> None:
        """Discard all work performed in this transaction."""
        if self._session is not None:
            self._session.rollback()
