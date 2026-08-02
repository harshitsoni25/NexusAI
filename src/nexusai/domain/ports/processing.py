"""Contracts for the data-processing framework.

Four ports cover the pluggable pieces of processing. A :class:`Transformer`
turns one value into another. A :class:`Rule` evaluates a record and reports an
outcome. A :class:`QualityDimensionAssessor` scores a dataset along one quality
dimension. A :class:`ChangeDetector` compares two datasets. Structural
validation reuses the existing :class:`~nexusai.domain.ports.validation.Validator`
port rather than introducing a fifth.

All are ``Protocol`` contracts (ADR-0003): an infrastructure implementation
satisfies them structurally, and a plugin adds a new transformer, rule, dimension
or detector without the engines changing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from nexusai.domain.model.assessment import QualityMeasurement, Severity
from nexusai.domain.model.change import ChangeSet
from nexusai.domain.model.rules import RuleOutcome
from nexusai.shared.types import JsonValue

if TYPE_CHECKING:
    from nexusai.domain.model.processing import ProcessedDataset, ProcessedRecord


@runtime_checkable
class Transformer(Protocol):
    """Turns one value into another, deterministically.

    A transformer performs a single, named conversion -- trim whitespace,
    normalise Unicode, parse a date. It is pure: the same input always yields the
    same output, with no clock, network or state, which is what lets a
    transformation chain be replayed and tested exactly.
    """

    @property
    def name(self) -> str:
        """A stable identifier used to register and select the transformer."""
        ...

    def transform(self, value: JsonValue) -> JsonValue:
        """Return the transformed value.

        Raises:
            TransformationError: If the value cannot be transformed and the
                transformer is configured to fail rather than pass the value
                through.
        """
        ...


@runtime_checkable
class Rule(Protocol):
    """Evaluates a record and reports whether a condition holds.

    A rule is the unit the rule engine runs and orders. It carries a priority, so
    the engine can run the most important rules first, and a group, so related
    rules can be enabled together. ``applies`` lets a rule opt out of records it
    does not concern, which is how conditional rules are expressed.
    """

    @property
    def name(self) -> str:
        """A stable identifier for the rule."""
        ...

    @property
    def priority(self) -> int:
        """The evaluation priority; lower numbers run first."""
        ...

    @property
    def group(self) -> str:
        """The group this rule belongs to, for enabling related rules together."""
        ...

    @property
    def severity(self) -> Severity:
        """The severity of a failure of this rule."""
        ...

    def applies(self, record: ProcessedRecord) -> bool:
        """Whether this rule should be evaluated against ``record``."""
        ...

    def evaluate(self, record: ProcessedRecord) -> RuleOutcome:
        """Evaluate the rule against ``record`` and return the outcome."""
        ...


@runtime_checkable
class QualityDimensionAssessor(Protocol):
    """Scores a dataset along one quality dimension.

    Where validation is per-record, a dimension assessor reads the whole dataset
    -- it cannot judge uniqueness or consistency from a single record -- and
    returns a normalised score with the counts behind it, so the score is
    explainable rather than opaque.
    """

    @property
    def dimension(self) -> str:
        """The name of the dimension this assessor scores."""
        ...

    def assess(self, dataset: ProcessedDataset) -> QualityMeasurement:
        """Score ``dataset`` along this dimension."""
        ...


@runtime_checkable
class ChangeDetector(Protocol):
    """Compares a current dataset against a previous one.

    A detector owns one notion of change -- content hash, field-by-field,
    record-set membership, document structure -- and reports it as a
    :class:`ChangeSet`. It holds no state between calls; the previous dataset is
    always supplied, which keeps detection reproducible.
    """

    @property
    def name(self) -> str:
        """A stable identifier used to register and select the detector."""
        ...

    def detect(self, current: ProcessedDataset, previous: ProcessedDataset) -> ChangeSet:
        """Return the changes from ``previous`` to ``current``."""
        ...


# Re-exported for the engines that consume a sequence of these ports.
__all__ = [
    "ChangeDetector",
    "QualityDimensionAssessor",
    "Rule",
    "Transformer",
]
