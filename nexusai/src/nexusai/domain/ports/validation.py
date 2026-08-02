"""The Validator contract.

A validator inspects a value and returns a :class:`ValidationResult` -- a verdict
plus the issues behind it. It never raises to signal that a value is invalid: an
invalid value is an ordinary, expected outcome and belongs in the returned
result, not in an exception. A validator raises only when it cannot perform the
check at all.

The rules a validator applies are domain policy, introduced with the engines
that own them. This is only the shape they conform to, so a plugin-supplied
validator and a built-in one are interchangeable.
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from nexusai.domain.model.assessment import ValidationResult

T_contra = TypeVar("T_contra", contravariant=True)


@runtime_checkable
class Validator(Protocol[T_contra]):
    """Inspects a value and reports what it found."""

    @property
    def name(self) -> str:
        """A stable identifier used to register and select the validator."""
        ...

    def validate(self, value: T_contra) -> ValidationResult:
        """Return the outcome of validating ``value``.

        Returns a result whether or not the value is valid. Raising is reserved
        for the case where validation itself cannot be carried out.
        """
        ...
