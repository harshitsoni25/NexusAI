"""The framework exception hierarchy.

Three rules give this hierarchy its operational meaning:

* **Retryability is a property of the exception type, not of the call site.**
  The retry middleware inspects ``retryable``, so retry behaviour is consistent
  everywhere in the framework and is tested in exactly one place.
* **Translation happens at the boundary where the foreign exception arises.**
  No ``httpx``, ``playwright`` or ``sqlalchemy`` exception type is ever allowed
  to propagate inward past the adapter that produced it.
* **Stack traces are always preserved** through exception chaining. Nothing is
  ever silently suppressed.

The hierarchy is the one approved in Phase 1, section 9.3.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any


class ErrorCategory(Enum):
    """Coarse classification used for reporting, metrics and log filtering.

    Categories are deliberately coarse. They answer "which subsystem failed?"
    for an operator scanning a report; the exception type answers "what exactly
    went wrong?" for an engineer reading a stack trace.
    """

    CONFIGURATION = "configuration"
    ACQUISITION = "acquisition"
    PARSING = "parsing"
    VALIDATION = "validation"
    QUALITY = "quality"
    STORAGE = "storage"
    EXPORT = "export"
    REPORT = "report"
    PLUGIN = "plugin"
    SCHEDULING = "scheduling"
    INTERNAL = "internal"


class NexusAIError(Exception):
    """Base class for every error raised by the framework.

    Carrying structured ``context`` alongside the message means a log line or a
    report entry can be filtered and aggregated on the offending key, URL or
    plugin name without anyone having to parse prose out of a message string.

    Args:
        message: Human-readable description of what went wrong.
        context: Structured detail about the failure. Values should be small and
            serialisable; do not attach large documents or secrets.
    """

    category: ErrorCategory = ErrorCategory.INTERNAL
    retryable: bool = False

    def __init__(self, message: str, /, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.context: Mapping[str, Any] = dict(context)

    def __str__(self) -> str:
        # A multi-line message has already been composed for a human to read;
        # appending the structured context to it only repeats what it says. The
        # context remains available programmatically either way.
        if not self.context or "\n" in self.message:
            return self.message
        detail = ", ".join(f"{key}={value!r}" for key, value in sorted(self.context.items()))
        return f"{self.message} ({detail})"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.message!r}, **{dict(self.context)!r})"

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation for logs and reports."""
        return {
            "type": type(self).__name__,
            "category": self.category.value,
            "message": self.message,
            "retryable": self.retryable,
            "context": dict(self.context),
        }


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #


class ConfigurationError(NexusAIError):
    """Configuration is missing, malformed, or fails validation.

    Always raised before execution begins. A misconfigured run must fail in
    under a second rather than after twenty minutes of scraping.
    """

    category = ErrorCategory.CONFIGURATION


# --------------------------------------------------------------------------- #
# Acquisition
# --------------------------------------------------------------------------- #


class AcquisitionError(NexusAIError):
    """A page or resource could not be acquired."""

    category = ErrorCategory.ACQUISITION


class NetworkError(AcquisitionError):
    """A transport-level failure occurred. Transient, therefore retryable."""

    retryable = True


class TimeoutError(AcquisitionError):  # noqa: A001 - deliberately shadows the builtin
    """An operation exceeded its configured deadline. Transient."""

    retryable = True


class HttpStatusError(AcquisitionError):
    """The server returned an unsuccessful status code.

    Retryability depends on the status class, so it is decided per instance
    rather than per type: server errors and rate-limit responses are worth
    retrying, client errors are not.
    """

    def __init__(self, message: str, /, *, status_code: int, **context: Any) -> None:
        super().__init__(message, status_code=status_code, **context)
        self.status_code = status_code
        self.retryable = status_code == 429 or 500 <= status_code < 600


class BrowserError(AcquisitionError):
    """The browser automation layer failed."""


# --------------------------------------------------------------------------- #
# Parsing and extraction
# --------------------------------------------------------------------------- #


class ParsingError(NexusAIError):
    """A document could not be interpreted."""

    category = ErrorCategory.PARSING


class DocumentParseError(ParsingError):
    """The document could not be parsed into a traversable structure."""


class ExtractionError(ParsingError):
    """An extractor failed while operating on a well-formed document.

    A selector that simply matches nothing is *not* an error: it is a recorded
    absence, which is what allows broken-selector detection to work later. This
    exception is for extractors that fail outright.
    """


# --------------------------------------------------------------------------- #
# Assessment
# --------------------------------------------------------------------------- #


class ValidationError(NexusAIError):
    """Validation of a record, schema or execution could not be carried out.

    A failing validation *result* is data, not an exception. This is raised only
    when validation itself cannot run.
    """

    category = ErrorCategory.VALIDATION


class QualityError(NexusAIError):
    """A data quality assessment could not be carried out."""

    category = ErrorCategory.QUALITY


class TransformationError(NexusAIError):
    """A value could not be transformed.

    Raised only by a transformer configured to fail on a value it cannot convert;
    the lenient default is to pass the original value through untouched, so that
    one unconvertible value does not abort processing of a whole record.
    """

    category = ErrorCategory.VALIDATION


# --------------------------------------------------------------------------- #
# Persistence and output
# --------------------------------------------------------------------------- #


class StorageError(NexusAIError):
    """A storage operation failed."""

    category = ErrorCategory.STORAGE


class TransactionError(StorageError):
    """A transaction could not be committed and was rolled back."""


class MigrationError(StorageError):
    """A schema migration failed."""


class ExportError(NexusAIError):
    """An export operation failed."""

    category = ErrorCategory.EXPORT


class ReportError(NexusAIError):
    """A report could not be generated."""

    category = ErrorCategory.REPORT


# --------------------------------------------------------------------------- #
# Plugins
# --------------------------------------------------------------------------- #


class PluginError(NexusAIError):
    """A plugin could not be loaded, registered or executed."""

    category = ErrorCategory.PLUGIN


class PluginLoadError(PluginError):
    """A plugin could not be imported or instantiated."""


class PluginContractError(PluginError):
    """A plugin does not satisfy the contract for its extension point."""


# --------------------------------------------------------------------------- #
# Scheduling and internal
# --------------------------------------------------------------------------- #


class SchedulingError(NexusAIError):
    """A scheduling operation failed."""

    category = ErrorCategory.SCHEDULING


class InternalError(NexusAIError):
    """An invariant of the framework itself was violated.

    Raising this always indicates a defect in the framework rather than a
    problem with configuration, a target site, or user input. It is never
    retryable and should never be caught to continue execution.
    """

    category = ErrorCategory.INTERNAL
