"""The framework exception hierarchy.

Re-exported here so that callers write ``from nexusai.domain.errors import
NetworkError`` rather than reaching into the module that defines it.
"""

from __future__ import annotations

from nexusai.domain.errors.exceptions import (
    AcquisitionError,
    BrowserError,
    ConfigurationError,
    DocumentParseError,
    ErrorCategory,
    ExportError,
    ExtractionError,
    HttpStatusError,
    InternalError,
    MigrationError,
    NetworkError,
    NexusAIError,
    ParsingError,
    PluginContractError,
    PluginError,
    PluginLoadError,
    QualityError,
    ReportError,
    SchedulingError,
    StorageError,
    TimeoutError,  # noqa: A004 - shadows the builtin deliberately; see exceptions.py
    TransactionError,
    TransformationError,
    ValidationError,
)

__all__ = [
    "AcquisitionError",
    "BrowserError",
    "ConfigurationError",
    "DocumentParseError",
    "ErrorCategory",
    "ExportError",
    "ExtractionError",
    "HttpStatusError",
    "InternalError",
    "MigrationError",
    "NetworkError",
    "NexusAIError",
    "ParsingError",
    "PluginContractError",
    "PluginError",
    "PluginLoadError",
    "QualityError",
    "ReportError",
    "SchedulingError",
    "StorageError",
    "TimeoutError",
    "TransactionError",
    "TransformationError",
    "ValidationError",
]
