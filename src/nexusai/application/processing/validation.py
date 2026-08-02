"""The validation engine.

Runs a set of structural validators over a processed record and merges their
findings into one :class:`ValidationResult`. Merging rather than short-circuiting
means a record's report lists every problem at once, not just the first, which is
what a user fixing a scraper needs.
"""

from __future__ import annotations

from collections.abc import Sequence

from nexusai.domain.model.assessment import ValidationResult
from nexusai.domain.model.processing import ProcessedRecord
from nexusai.domain.ports.validation import Validator


class ValidationEngine:
    """Runs structural validators over a record and merges their results."""

    def __init__(self, validators: Sequence[Validator[ProcessedRecord]]) -> None:
        self._validators = tuple(validators)

    def validate(self, record: ProcessedRecord) -> ValidationResult:
        """Validate ``record`` with every validator and merge the findings."""
        result = ValidationResult.passing(checked=0)
        for validator in self._validators:
            result = result.merge(validator.validate(record))
        return result
