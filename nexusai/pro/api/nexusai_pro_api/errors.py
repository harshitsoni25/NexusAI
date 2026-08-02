"""Consistent error handling: engine exceptions mapped to HTTP responses.

The engine raises a hierarchy rooted at ``NexusAIError``, each carrying an
``ErrorCategory``. These handlers translate that hierarchy into stable HTTP status
codes and a single error envelope, so clients get predictable, machine-readable
errors without the API leaking tracebacks or engine internals.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from nexusai.domain.errors.exceptions import (
    AcquisitionError,
    ConfigurationError,
    ExportError,
    InternalError,
    NexusAIError,
    PluginError,
    QualityError,
    ReportError,
    SchedulingError,
    StorageError,
    ValidationError,
)
from nexusai_pro_api.logging_config import get_logger, request_id_var

logger = get_logger("errors")


class ApiError(Exception):
    """An error raised by the API layer itself (e.g. a missing resource)."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def not_found(resource: str, identifier: str) -> ApiError:
    return ApiError(status.HTTP_404_NOT_FOUND, "not_found", f"{resource} '{identifier}' was not found")


# Engine exception -> HTTP status. Order matters: most specific first.
_STATUS_BY_TYPE: list[tuple[type[NexusAIError], int]] = [
    (ConfigurationError, status.HTTP_400_BAD_REQUEST),
    (ValidationError, status.HTTP_422_UNPROCESSABLE_ENTITY),
    (QualityError, status.HTTP_422_UNPROCESSABLE_ENTITY),
    (AcquisitionError, status.HTTP_502_BAD_GATEWAY),
    (PluginError, status.HTTP_400_BAD_REQUEST),
    (ExportError, status.HTTP_500_INTERNAL_SERVER_ERROR),
    (ReportError, status.HTTP_500_INTERNAL_SERVER_ERROR),
    (StorageError, status.HTTP_500_INTERNAL_SERVER_ERROR),
    (SchedulingError, status.HTTP_409_CONFLICT),
    (InternalError, status.HTTP_500_INTERNAL_SERVER_ERROR),
]


def _status_for(exc: NexusAIError) -> int:
    for exc_type, code in _STATUS_BY_TYPE:
        if isinstance(exc, exc_type):
            return code
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def _envelope(*, code: str, message: str, category: str | None = None) -> dict[str, object]:
    body: dict[str, object] = {
        "error": {"code": code, "message": message, "request_id": request_id_var.get()}
    }
    if category is not None:
        body["error"]["category"] = category
    return body


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the API and engine exception handlers to the application."""

    @app.exception_handler(ApiError)
    async def _handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code=exc.code, message=exc.message),
        )

    @app.exception_handler(NexusAIError)
    async def _handle_engine_error(_: Request, exc: NexusAIError) -> JSONResponse:
        http_status = _status_for(exc)
        category = getattr(getattr(exc, "category", None), "value", None)
        code = type(exc).__name__
        if http_status >= 500:
            logger.exception("engine error: %s", code)
        else:
            logger.warning("engine error: %s: %s", code, exc)
        return JSONResponse(
            status_code=http_status,
            content=_envelope(code=code, message=str(exc), category=category),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unexpected error")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope(code="internal_error", message="An unexpected error occurred"),
        )
