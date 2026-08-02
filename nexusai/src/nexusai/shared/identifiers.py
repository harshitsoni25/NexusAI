"""Strongly typed identifiers.

Identifiers are wrapper value objects rather than bare strings so that a job
identifier can never be passed where a run identifier is expected. Generation is
deliberately absent: it requires a source of randomness, which is an effect, so
it lives behind the ``IdGenerator`` port instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class Identifier:
    """Base class for opaque string identifiers."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError(f"{type(self).__name__} must be a non-empty string")

    def __str__(self) -> str:
        return self.value

    @classmethod
    def of(cls, value: str) -> Self:
        """Construct an identifier from ``value``, stripping surrounding space."""
        return cls(value.strip())


@dataclass(frozen=True, slots=True)
class CorrelationId(Identifier):
    """Ties every log line, metric and event of a single execution together."""


@dataclass(frozen=True, slots=True)
class JobId(Identifier):
    """Identifies a job definition across all of its runs."""


@dataclass(frozen=True, slots=True)
class RunId(Identifier):
    """Identifies a single execution of a job."""
