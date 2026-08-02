"""Shared response models used across routers."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Stable machine-readable error code.")
    message: str = Field(..., description="Human-readable explanation.")
    request_id: str = Field(..., description="Correlates the error with server logs.")
    category: str | None = Field(default=None, description="Engine error category, when applicable.")


class ErrorResponse(BaseModel):
    error: ErrorDetail


class Message(BaseModel):
    message: str
