"""Shared test fixtures.

Everything here is deterministic. No test in this suite touches the network, and
the only filesystem access is to a temporary directory, which is what makes the
suite safe to run anywhere and repeatable everywhere.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine
from sqlalchemy import create_engine as _sqlalchemy_create_engine

from nexusai.composition.container import Container, build_container
from nexusai.domain.model.context import FrameworkContext
from nexusai.domain.model.execution import ConfigurationSnapshot
from nexusai.infrastructure.config.loader import ConfigurationLoader, LoadedConfiguration
from nexusai.infrastructure.observability.metrics import InMemoryMetricsSink
from nexusai.shared.identifiers import CorrelationId
from nexusai.testing import FrozenClock, RecordingLogger, SequentialIdGenerator


@pytest.fixture(autouse=True)
def _dispose_sqlite_engines(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Dispose every SQLite engine created during a test.

    All engines funnel through ``create_sqlite_engine``, which calls the
    module-local ``create_engine``. Patching that one symbol captures every engine
    created by any caller (tests and composition alike) so their pooled
    ``sqlite3.Connection`` is closed at teardown instead of at GC. On Python 3.13 an
    un-closed connection collected by GC raises ``ResourceWarning`` -> pytest turns
    it into ``PytestUnraisableExceptionWarning`` -> error under ``filterwarnings``.
    """
    created: list[Engine] = []

    def _tracking(*args: Any, **kwargs: Any) -> Engine:
        engine: Engine = _sqlalchemy_create_engine(*args, **kwargs)
        created.append(engine)
        return engine

    monkeypatch.setattr("nexusai.infrastructure.persistence.engine.create_engine", _tracking)
    try:
        yield
    finally:
        for engine in created:
            engine.dispose()


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove real NEXUSAI_* variables from the process environment.

    Without this, a developer who exports a variable in their shell gets
    different test results from CI -- the exact non-determinism section 42
    prohibits.
    """
    import os

    for name in [key for key in os.environ if key.startswith("NEXUSAI_")]:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def clock() -> FrozenClock:
    """A clock that only moves when a test tells it to."""
    return FrozenClock()


@pytest.fixture
def ids() -> SequentialIdGenerator:
    """Predictable identifiers, so generated values can be asserted on."""
    return SequentialIdGenerator()


@pytest.fixture
def logger() -> RecordingLogger:
    """A logger that keeps every record for inspection."""
    return RecordingLogger()


@pytest.fixture
def metrics() -> InMemoryMetricsSink:
    """A metrics sink that keeps every measurement."""
    return InMemoryMetricsSink()


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """An empty directory for configuration files written by a test."""
    directory = tmp_path / "config"
    directory.mkdir()
    return directory


@pytest.fixture
def loader(tmp_path: Path) -> ConfigurationLoader:
    """A loader with no packaged defaults, so tests control every layer."""
    return ConfigurationLoader(packaged_defaults=None)


@pytest.fixture
def configuration(loader: ConfigurationLoader, tmp_path: Path) -> LoadedConfiguration:
    """A minimal valid configuration rooted in a temporary directory."""
    return loader.load(
        overrides=(f"paths.root={tmp_path / 'runtime'}",),
        environ={},
        dotenv_path=tmp_path / "absent.env",
    )


@pytest.fixture
def container(
    configuration: LoadedConfiguration,
    clock: FrozenClock,
    ids: SequentialIdGenerator,
    logger: RecordingLogger,
    metrics: InMemoryMetricsSink,
) -> Iterator[Container]:
    """A fully wired container built entirely from test doubles."""
    yield build_container(
        configuration, clock=clock, id_generator=ids, logger=logger, metrics=metrics
    )


@pytest.fixture
def framework_context(
    clock: FrozenClock,
    ids: SequentialIdGenerator,
    logger: RecordingLogger,
    metrics: InMemoryMetricsSink,
) -> FrameworkContext:
    """A FrameworkContext assembled entirely from test doubles."""
    return FrameworkContext(
        logger=logger,
        metrics=metrics,
        clock=clock,
        id_generator=ids,
        correlation_id=CorrelationId("test-correlation"),
        configuration=ConfigurationSnapshot(values={"env": "test"}, origins={"env": "defaults"}),
    )


# --- Phase 6 downstream fixtures ---------------------------------------------
from downstream_builders import make_dataset  # noqa: E402
from nexusai.domain.model.processing import ProcessedDataset  # noqa: E402
from nexusai.infrastructure.persistence import (  # noqa: E402
    SqlAlchemyDatasetVersionStore,
    create_session_factory,
    create_sqlite_engine,
    initialise_schema,
)


@pytest.fixture
def dataset() -> ProcessedDataset:
    """A small processed dataset with a full processing context."""
    return make_dataset()


@pytest.fixture
def store() -> SqlAlchemyDatasetVersionStore:
    """A fresh in-memory dataset version store."""
    engine = create_sqlite_engine()
    initialise_schema(engine)
    return SqlAlchemyDatasetVersionStore(create_session_factory(engine))


@pytest.fixture
def out_dir(tmp_path: Path) -> Path:
    """An isolated output directory for exporters and renderers."""
    directory = tmp_path / "out"
    directory.mkdir()
    return directory
