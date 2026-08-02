"""Structured logging for the API, with per-request correlation identifiers.

A ``contextvar`` carries a request id through the handling of a single request so
every log line emitted while serving it can be correlated. This mirrors the engine's
own correlation-id discipline (ADR-0012) without importing engine internals.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def new_request_id() -> str:
    """Mint a short, unique identifier for one request."""
    return uuid.uuid4().hex[:16]


class _JsonFormatter(logging.Formatter):
    """Render records as single-line JSON including the current request id."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class _TextFormatter(logging.Formatter):
    """A human-readable formatter for local development."""

    def format(self, record: logging.LogRecord) -> str:
        base = (
            f"{record.levelname:<7} [{request_id_var.get()}] {record.name}: {record.getMessage()}"
        )
        if record.exc_info:
            base = f"{base}\n{self.formatException(record.exc_info)}"
        return base


def configure_logging(*, level: str = "INFO", as_json: bool = True) -> None:
    """Install a single stdout handler for the API's logger hierarchy."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter() if as_json else _TextFormatter())

    root = logging.getLogger("nexusai_pro_api")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced child logger under the API's root."""
    return logging.getLogger(f"nexusai_pro_api.{name}")
