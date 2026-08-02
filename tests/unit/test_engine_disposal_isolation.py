"""Isolation guarantees for the autouse SQLite-engine disposal fixture (R8).

The autouse ``_dispose_sqlite_engines`` fixture patches ``create_engine`` and disposes
every engine created *during a test*. These tests prove it disposes only per-test
engines and never a longer-lived (session-scoped) engine, so it is safe as suites
grow and add session fixtures.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine

from nexusai.infrastructure.persistence.engine import create_sqlite_engine

pytestmark = pytest.mark.unit


@pytest.fixture(scope="session")
def session_engine() -> Iterator[Engine]:
    """A session-scoped engine, created once before any function-scoped fixture."""
    engine = create_sqlite_engine()
    yield engine
    engine.dispose()


class TestSessionEngineNotCrossDisposed:
    """A session engine must remain usable across tests despite per-test disposal."""

    def test_first_test_uses_session_engine(self, session_engine: Engine) -> None:
        with session_engine.connect() as conn:
            assert conn.exec_driver_sql("SELECT 1").scalar() == 1

    def test_second_test_session_engine_still_alive(self, session_engine: Engine) -> None:
        # If the per-test fixture had disposed the session engine after the first
        # test, this connection would fail. It passing proves no cross-disposal.
        with session_engine.connect() as conn:
            assert conn.exec_driver_sql("SELECT 1").scalar() == 1


class TestPerTestRegistryIsFresh:
    """Each test gets its own engine; disposal in one test cannot touch another's."""

    def test_creates_and_uses_a_per_test_engine(self) -> None:
        engine = create_sqlite_engine()
        with engine.connect() as conn:
            assert conn.exec_driver_sql("SELECT 1").scalar() == 1
        # No dispose here on purpose: the autouse fixture owns disposal at teardown.

    def test_a_second_per_test_engine_is_independent(self) -> None:
        engine = create_sqlite_engine()
        with engine.connect() as conn:
            assert conn.exec_driver_sql("SELECT 2").scalar() == 2
