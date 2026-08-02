"""A minimal ``Result`` type for expected, non-exceptional failures.

Exceptions remain the mechanism for genuinely exceptional conditions. This type
is for outcomes where failure is an ordinary part of the contract and the caller
is always expected to handle it -- plugin loading, per-item processing, and
validation checks, where raising would force control flow through a mechanism
designed for the unusual case.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import NoReturn, TypeGuard


@dataclass(frozen=True, slots=True)
class Ok[T]:
    """A successful outcome carrying a value."""

    value: T

    def unwrap(self) -> T:
        """Return the contained value."""
        return self.value

    def unwrap_or(self, default: T) -> T:  # noqa: ARG002 - unused on the success path
        """Return the contained value, ignoring ``default``."""
        return self.value

    def map[U](self, func: Callable[[T], U]) -> Ok[U]:
        """Apply ``func`` to the contained value."""
        return Ok(func(self.value))


@dataclass(frozen=True, slots=True)
class Err[E]:
    """A failed outcome carrying an error."""

    error: E

    def unwrap(self) -> NoReturn:
        """Raise, because there is no value to return."""
        raise ValueError(f"Called unwrap() on an Err: {self.error!r}")

    def unwrap_or[T](self, default: T) -> T:
        """Return ``default``, because there is no contained value."""
        return default

    def map[U](self, func: Callable[..., U]) -> Err[E]:  # noqa: ARG002 - never applied
        """Return the error unchanged; ``func`` is never applied."""
        return self


type Result[T, E] = Ok[T] | Err[E]
"""Alias for readability at call sites, as in ``Result[Plugin, LoadFailure]``."""


def is_ok[T, E](result: Ok[T] | Err[E]) -> TypeGuard[Ok[T]]:
    """Narrow ``result`` to :class:`Ok`."""
    return isinstance(result, Ok)


def is_err[T, E](result: Ok[T] | Err[E]) -> TypeGuard[Err[E]]:
    """Narrow ``result`` to :class:`Err`."""
    return isinstance(result, Err)
