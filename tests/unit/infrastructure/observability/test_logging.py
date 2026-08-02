"""The Loguru adapter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nexusai.infrastructure.config.settings import (
    ConsoleLogSettings,
    FileLogSettings,
    LogFormat,
    LoggingSettings,
    LogLevel,
    PathSettings,
)
from nexusai.infrastructure.observability.correlation import bind_log_context, correlation_scope
from nexusai.infrastructure.observability.logging import (
    LoguruLogger,
    _console_format,
    configure_logging,
)
from nexusai.shared.identifiers import CorrelationId


@dataclass
class FakeBackend:
    """Stands in for the Loguru singleton, capturing what the adapter asks of it."""

    calls: list[tuple[str, str, Mapping[str, Any]]] = field(default_factory=list)
    sinks: list[dict[str, Any]] = field(default_factory=list)
    removed: int = 0
    _pending: Mapping[str, Any] = field(default_factory=dict)

    def opt(self, **_: Any) -> FakeBackend:
        return self

    def bind(self, **fields: Any) -> FakeBackend:
        self._pending = fields
        return self

    def log(self, level: str, message: str) -> None:
        self.calls.append((level, message, dict(self._pending)))
        self._pending = {}

    def add(self, sink: Any, **options: Any) -> int:
        self.sinks.append({"sink": sink, **options})
        return len(self.sinks)

    def remove(self, handler_id: int | None = None) -> None:
        self.removed += 1


def test_each_level_reaches_the_backend() -> None:
    backend = FakeBackend()
    logger = LoguruLogger(backend)
    logger.debug("d")
    logger.info("i")
    logger.warning("w")
    logger.error("e")
    logger.critical("c")
    assert [level for level, _, _ in backend.calls] == [
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ]


def test_call_fields_are_attached() -> None:
    backend = FakeBackend()
    LoguruLogger(backend).info("started", site="example")
    assert backend.calls[0][2]["site"] == "example"


def test_bound_fields_persist_across_calls() -> None:
    backend = FakeBackend()
    logger = LoguruLogger(backend).bind(job_id="j-1")
    logger.info("one")
    logger.info("two")
    assert all(record[2]["job_id"] == "j-1" for record in backend.calls)


def test_binding_does_not_mutate_the_parent_logger() -> None:
    backend = FakeBackend()
    parent = LoguruLogger(backend)
    parent.bind(job_id="j-1").info("child")
    parent.info("parent")
    assert "job_id" in backend.calls[0][2]
    assert "job_id" not in backend.calls[1][2]


def test_ambient_context_is_attached_without_being_passed() -> None:
    backend = FakeBackend()
    with correlation_scope(CorrelationId("c-1")), bind_log_context(stage="extract"):
        LoguruLogger(backend).info("working")
    fields = backend.calls[0][2]
    assert fields["correlation_id"] == "c-1"
    assert fields["stage"] == "extract"


def test_call_fields_take_precedence_over_bound_and_ambient_fields() -> None:
    backend = FakeBackend()
    with bind_log_context(stage="ambient"):
        LoguruLogger(backend).bind(stage="bound").info("x", stage="call")
    assert backend.calls[0][2]["stage"] == "call"


def test_exception_logs_at_error() -> None:
    backend = FakeBackend()
    LoguruLogger(backend).exception("failed")
    assert backend.calls[0][0] == "ERROR"


def test_configure_installs_a_console_sink_and_clears_existing_ones() -> None:
    backend = FakeBackend()
    configure_logging(LoggingSettings(), PathSettings(), backend=backend)
    # Repeated configuration must not duplicate every log line.
    assert backend.removed == 1
    assert len(backend.sinks) == 1


def test_the_file_sink_is_added_and_its_directory_created(tmp_path: Path) -> None:
    backend = FakeBackend()
    settings = LoggingSettings(file=FileLogSettings(enabled=True))
    paths = PathSettings(root=tmp_path)
    configure_logging(settings, paths, backend=backend)
    assert len(backend.sinks) == 2
    assert paths.resolve("logs").exists()


def test_a_disabled_console_produces_no_sink() -> None:
    backend = FakeBackend()
    configure_logging(
        LoggingSettings(console=ConsoleLogSettings(enabled=False)), PathSettings(), backend=backend
    )
    assert backend.sinks == []


def test_json_console_output_uses_serialisation() -> None:
    backend = FakeBackend()
    configure_logging(
        LoggingSettings(console=ConsoleLogSettings(format=LogFormat.JSON)),
        PathSettings(),
        backend=backend,
    )
    assert backend.sinks[0]["serialize"] is True


def test_the_global_floor_overrides_a_more_permissive_sink() -> None:
    backend = FakeBackend()
    configure_logging(
        LoggingSettings(level=LogLevel.WARNING, console=ConsoleLogSettings(level=LogLevel.DEBUG)),
        PathSettings(),
        backend=backend,
    )
    assert backend.sinks[0]["level"] == "WARNING"


def test_a_stricter_sink_than_the_floor_is_respected() -> None:
    backend = FakeBackend()
    configure_logging(
        LoggingSettings(level=LogLevel.DEBUG, console=ConsoleLogSettings(level=LogLevel.ERROR)),
        PathSettings(),
        backend=backend,
    )
    assert backend.sinks[0]["level"] == "ERROR"


def test_field_values_containing_braces_cannot_become_placeholders() -> None:
    # Scraped content ends up in log fields. A value containing braces must not
    # be interpreted as a format placeholder.
    rendered = _console_format({"extra": {"value": "{oops}"}})
    assert "{{oops}}" in rendered


def test_no_fields_means_no_trailing_separator() -> None:
    assert _console_format({"extra": {}}).endswith("\n{exception}")
