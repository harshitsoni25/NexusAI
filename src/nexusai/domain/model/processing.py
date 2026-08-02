"""The processed dataset and the context that describes how it was produced.

Processing transforms raw extracted values into trusted ones, but it must never
destroy the originals. That constraint shapes these models: a
:class:`ProcessedField` holds both the ``raw_value`` it started from and the
``value`` it became, plus the ordered list of transformations applied, so the
derivation is always recoverable. A :class:`ProcessedRecord` keeps the entire
original :class:`ExtractionResult` as ``raw`` alongside its processed fields.
Nothing here mutates extraction output; processing produces a new representation
beside it.

A :class:`ProcessedDataset` gathers records with a :class:`ProcessingContext`
that records when and how processing ran -- versions, configuration, and the
validation, quality and change summaries -- so the dataset is self-describing
when it reaches storage in a later phase.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from nexusai.domain.model.assessment import QualityResult, ValidationResult
from nexusai.domain.model.change import ChangeSummary
from nexusai.domain.model.execution import ConfigurationSnapshot
from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.quality import QualityGrade
from nexusai.domain.provenance.source import SourceReference
from nexusai.shared.types import JsonValue


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessedField:
    """A single field after transformation, retaining its raw origin.

    Attributes:
        name: The field name.
        value: The transformed value.
        raw_value: The value before any transformation, preserved unchanged.
        transformations: The names of the transformers applied, in order, so the
            path from ``raw_value`` to ``value`` is auditable.
    """

    name: str
    value: JsonValue
    raw_value: JsonValue
    transformations: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "transformations", tuple(self.transformations))

    @property
    def was_changed(self) -> bool:
        """Whether transformation altered the value."""
        return self.value != self.raw_value

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "name": self.name,
            "value": self.value,
            "raw_value": self.raw_value,
            "transformations": list(self.transformations),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessedRecord:
    """One extracted record after transformation, validation and assessment.

    Attributes:
        identity: A stable key identifying this record across dataset versions,
            used by change detection. Derived from a key field or a content hash.
        raw: The original extraction output, preserved immutably.
        fields: The processed fields, keyed by name.
        validation: The structural and rule validation result for this record.
        quality: The per-record quality result, when assessed at record level.
        retrieved_at: When the source document was retrieved, carried through for
            the timeliness dimension.
        source: The provenance root of the source document.
    """

    identity: str
    raw: ExtractionResult
    fields: Mapping[str, ProcessedField] = field(default_factory=dict)
    validation: ValidationResult = field(default_factory=ValidationResult)
    quality: QualityResult = field(default_factory=QualityResult)
    retrieved_at: datetime | None = None
    source: SourceReference | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", dict(self.fields))

    def value(self, name: str) -> JsonValue:
        """Return the processed value of ``name``, or ``None`` if absent."""
        processed = self.fields.get(name)
        return processed.value if processed is not None else None

    def values(self) -> Mapping[str, JsonValue]:
        """Return a plain mapping of processed field names to values."""
        return {name: processed.value for name, processed in self.fields.items()}

    def with_validation(self, validation: ValidationResult) -> ProcessedRecord:
        """Return a copy carrying ``validation``, leaving this record unchanged."""
        return _replace_record(self, validation=validation)

    def with_quality(self, quality: QualityResult) -> ProcessedRecord:
        """Return a copy carrying ``quality``, leaving this record unchanged."""
        return _replace_record(self, quality=quality)

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation, including preserved raw values."""
        return {
            "identity": self.identity,
            "fields": {name: processed.to_dict() for name, processed in self.fields.items()},
            "validation": self.validation.to_dict(),
            "quality": self.quality.to_dict(),
            "retrieved_at": self.retrieved_at.isoformat() if self.retrieved_at else None,
            "raw": self.raw.to_dict(),
            "source": self.source.to_dict() if self.source else None,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessingContext:
    """Metadata describing how a dataset was processed.

    Attached to every processed dataset so that, by the time it reaches storage,
    it can answer "when, with what versions, under what configuration, and with
    what result?" without reference to the run that produced it.

    Attributes:
        processed_at: When processing completed, in UTC.
        framework_version: The version of the framework that processed the data.
        rule_version: The version of the rule configuration applied.
        configuration: A snapshot of the effective processing configuration.
        validation_summary: A roll-up of validation across the dataset.
        quality: The dataset-level quality result.
        quality_grade: The letter grade the quality score earned.
        change_summary: A roll-up of detected changes.
        sources: The provenance roots of the source documents.
    """

    processed_at: datetime
    framework_version: str
    rule_version: str = "unversioned"
    configuration: ConfigurationSnapshot = field(default_factory=ConfigurationSnapshot)
    validation_summary: ValidationResult = field(default_factory=ValidationResult)
    quality: QualityResult = field(default_factory=QualityResult)
    quality_grade: QualityGrade = QualityGrade.F
    change_summary: ChangeSummary = field(default_factory=ChangeSummary)
    sources: Sequence[SourceReference] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "sources", tuple(self.sources))

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "processed_at": self.processed_at.isoformat(),
            "framework_version": self.framework_version,
            "rule_version": self.rule_version,
            "configuration": self.configuration.to_dict(),
            "validation_summary": self.validation_summary.to_dict(),
            "quality": self.quality.to_dict(),
            "quality_grade": self.quality_grade.value,
            "change_summary": self.change_summary.to_dict(),
            "sources": [source.to_dict() for source in self.sources],
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessedDataset:
    """A collection of processed records with the context of their processing.

    The output of the processing pipeline and the input to storage in a later
    phase. It is self-describing: the records carry their preserved raw values
    and per-record results, and the context carries the dataset-level summaries.
    """

    records: Sequence[ProcessedRecord] = field(default_factory=tuple)
    context: ProcessingContext | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", tuple(self.records))

    def __len__(self) -> int:
        return len(self.records)

    @property
    def is_valid(self) -> bool:
        """Whether every record passed validation."""
        return all(record.validation.is_valid for record in self.records)

    def with_context(self, context: ProcessingContext) -> ProcessedDataset:
        """Return a copy carrying ``context``."""
        return ProcessedDataset(records=self.records, context=context)

    def with_records(self, records: Sequence[ProcessedRecord]) -> ProcessedDataset:
        """Return a copy with ``records`` replaced, keeping the context."""
        return ProcessedDataset(records=records, context=self.context)

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "records": [record.to_dict() for record in self.records],
            "context": self.context.to_dict() if self.context else None,
        }


def _replace_record(record: ProcessedRecord, **changes: Any) -> ProcessedRecord:
    """Return a copy of ``record`` with ``changes`` applied."""
    current: dict[str, Any] = {
        "identity": record.identity,
        "raw": record.raw,
        "fields": dict(record.fields),
        "validation": record.validation,
        "quality": record.quality,
        "retrieved_at": record.retrieved_at,
        "source": record.source,
    }
    current.update(changes)
    return ProcessedRecord(**current)
