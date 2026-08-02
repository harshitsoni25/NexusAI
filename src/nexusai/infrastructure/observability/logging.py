"""Loguru adapter implementing the ``Logger`` port.

Components depend on the port, never on Loguru. Two things follow. Swapping the
logging backend touches this module only. More usefully day to day, a unit test
can inject a recording logger and assert on what was logged, which is impossible
when components call a library singleton directly.

Loguru's module-level ``logger`` is global mutable state. It is confined to this
adapter and configured exactly once, by the composition root; nothing else in
the framework may import it.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from loguru import logger as _loguru_logger

from nexusai.infrastructure.config.settings import (
    ConsoleLogSettings,
    FileLogSettings,
    LogFormat,
    LoggingSettings,
    PathSettings,
)
from nexusai.infrastructure.observability.correlation import (
    current_correlation_id,
    current_log_context,
)

_CONSOLE_BASE = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


class LoguruLogger:
    """Structured logger backed by Loguru.

    Contextual fields are assembled at call time from three places, in order of
    increasing specificity: the ambient correlation context, fields bound to this
    logger instance, and fields passed to the call itself.
    """

    __slots__ = ("_bound", "_logger")

    def __init__(self, backend: Any = _loguru_logger, bound: Mapping[str, Any] | None = None):
        self._logger = backend
        self._bound: Mapping[str, Any] = dict(bound or {})

    def bind(self, **fields: Any) -> LoguruLogger:
        """Return a logger that attaches ``fields`` to every subsequent record."""
        return LoguruLogger(self._logger, {**self._bound, **fields})

    def debug(self, message: str, /, **fields: Any) -> None:
        """Log diagnostic detail useful only when investigating a problem."""
        self._emit("DEBUG", message, fields)

    def info(self, message: str, /, **fields: Any) -> None:
        """Log a normal, noteworthy occurrence."""
        self._emit("INFO", message, fields)

    def warning(self, message: str, /, **fields: Any) -> None:
        """Log a recoverable problem an operator should eventually see."""
        self._emit("WARNING", message, fields)

    def error(self, message: str, /, **fields: Any) -> None:
        """Log a failure that prevented an operation from completing."""
        self._emit("ERROR", message, fields)

    def critical(self, message: str, /, **fields: Any) -> None:
        """Log a failure that prevents the framework from continuing."""
        self._emit("CRITICAL", message, fields)

    def exception(self, message: str, /, **fields: Any) -> None:
        """Log at ERROR with the active exception's traceback attached."""
        self._emit("ERROR", message, fields, with_exception=True)

    def _emit(
        self,
        level: str,
        message: str,
        fields: Mapping[str, Any],
        *,
        with_exception: bool = False,
    ) -> None:
        extra: dict[str, Any] = {}
        correlation_id = current_correlation_id()
        if correlation_id is not None:
            extra["correlation_id"] = str(correlation_id)
        extra.update(current_log_context())
        extra.update(self._bound)
        extra.update(fields)
        # depth=2 attributes the record to the caller rather than to this module.
        self._logger.opt(depth=2, exception=with_exception).bind(**extra).log(level, message)


def _console_format(record: Mapping[str, Any]) -> str:
    """Build a Loguru format string that appends contextual fields.

    Returning a format string rather than a rendered line is Loguru's contract
    for callable formatters, so field values are escaped to prevent a scraped
    value containing braces from being interpreted as a placeholder.
    """
    extra: Mapping[str, Any] = record.get("extra", {})
    suffix = ""
    if extra:
        rendered = " ".join(f"{key}={value}" for key, value in sorted(extra.items()))
        escaped = rendered.replace("{", "{{").replace("}", "}}").replace("<", r"\<")
        suffix = f" <dim>| {escaped}</dim>"
    return _CONSOLE_BASE + suffix + "\n{exception}"


def configure_logging(
    settings: LoggingSettings,
    paths: PathSettings,
    *,
    backend: Any = _loguru_logger,
) -> LoguruLogger:
    """Install the configured sinks and return the root logger.

    Called exactly once, by the composition root. Existing handlers are removed
    first so that repeated configuration -- in tests, or across CLI invocations
    in one process -- does not duplicate every log line.

    Args:
        settings: Logging configuration.
        paths: Used to resolve the log directory when file logging is enabled.
        backend: Injection point for tests; defaults to the Loguru singleton.
    """
    backend.remove()
    if settings.console.enabled:
        _add_console_sink(backend, settings, settings.console)
    if settings.file.enabled:
        _add_file_sink(backend, settings, settings.file, paths)
    return LoguruLogger(backend)


def _effective_level(settings: LoggingSettings, sink_level: str) -> str:
    """Return the stricter of the global floor and the sink's own level."""
    order = ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
    return max(settings.level.value, sink_level, key=order.index)


def _add_console_sink(backend: Any, settings: LoggingSettings, console: ConsoleLogSettings) -> None:
    level = _effective_level(settings, console.level.value)
    if console.format is LogFormat.JSON:
        backend.add(
            sys.stderr, level=level, serialize=True, backtrace=True, diagnose=settings.diagnose
        )
        return
    backend.add(
        sys.stderr,
        level=level,
        format=_console_format,
        colorize=console.colorize,
        backtrace=True,
        diagnose=settings.diagnose,
    )


def _add_file_sink(
    backend: Any, settings: LoggingSettings, file: FileLogSettings, paths: PathSettings
) -> None:
    directory: Path = paths.resolve("logs")
    directory.mkdir(parents=True, exist_ok=True)
    backend.add(
        directory / file.filename,
        level=_effective_level(settings, file.level.value),
        serialize=file.format is LogFormat.JSON,
        format=_console_format if file.format is LogFormat.CONSOLE else "{message}",
        rotation=file.rotation,
        retention=file.retention,
        compression=file.compression,
        enqueue=True,
        backtrace=True,
        diagnose=settings.diagnose,
    )
