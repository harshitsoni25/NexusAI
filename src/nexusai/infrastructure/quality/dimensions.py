"""The six data-quality dimensions.

Each assessor reads a whole :class:`ProcessedDataset` and returns a normalised
score in ``[0, 1]`` for one dimension, with the counts behind it recorded in the
measurement's detail so the number is explainable. Dataset-level rather than
per-record because several of these questions -- is this value unique? is this
field consistently typed? -- have no meaning for a single record.

The assessors are deterministic given a dataset. Timeliness is the one that
depends on "now", so it takes an explicit reference instant rather than reading a
clock, keeping it as reproducible as the others.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from nexusai.domain.model.assessment import QualityMeasurement
from nexusai.domain.model.processing import ProcessedDataset, ProcessedRecord
from nexusai.domain.model.quality import QualityDimension
from nexusai.shared.types import JsonValue


def _is_present(value: JsonValue) -> bool:
    return value is not None and not (isinstance(value, str) and not value.strip())


def _measure(
    dimension: QualityDimension, score: float, weight: float, **detail: JsonValue
) -> QualityMeasurement:
    return QualityMeasurement(
        dimension=dimension.value, score=score, weight=weight, detail=dict(detail)
    )


class CompletenessDimension:
    """Scores the fraction of expected field values that are present.

    Args:
        fields: The fields expected on every record. Completeness is the ratio of
            present values to the total expected across the dataset.
        weight: This dimension's weight in the composite score.
    """

    dimension = QualityDimension.COMPLETENESS.value

    def __init__(self, fields: Sequence[str], *, weight: float = 1.0) -> None:
        self._fields = tuple(fields)
        self._weight = weight

    def assess(self, dataset: ProcessedDataset) -> QualityMeasurement:
        """Score completeness across the dataset's records."""
        expected = len(self._fields) * len(dataset.records)
        if expected == 0:
            return _measure(QualityDimension.COMPLETENESS, 1.0, self._weight, expected=0)
        present = sum(
            1
            for record in dataset.records
            for name in self._fields
            if _is_present(record.value(name))
        )
        return _measure(
            QualityDimension.COMPLETENESS,
            present / expected,
            self._weight,
            present=present,
            expected=expected,
        )


class AccuracyDimension:
    """Scores the fraction of records that passed validation.

    Accuracy here means "the data conforms to its rules": a record whose
    validation result is valid counts as accurate. It reuses the validation
    already attached to each record rather than re-checking.
    """

    dimension = QualityDimension.ACCURACY.value

    def __init__(self, *, weight: float = 1.0) -> None:
        self._weight = weight

    def assess(self, dataset: ProcessedDataset) -> QualityMeasurement:
        """Score accuracy as the fraction of valid records."""
        if not dataset.records:
            return _measure(QualityDimension.ACCURACY, 1.0, self._weight, records=0)
        valid = sum(1 for record in dataset.records if record.validation.is_valid)
        return _measure(
            QualityDimension.ACCURACY,
            valid / len(dataset.records),
            self._weight,
            valid=valid,
            records=len(dataset.records),
        )


class ConsistencyDimension:
    """Scores whether each field holds a consistent type across records.

    For every field, the most common Python type among its present values is
    taken as the norm; consistency is the fraction of present values matching
    their field's norm. A dataset where ``price`` is sometimes a number and
    sometimes a string scores below one.
    """

    dimension = QualityDimension.CONSISTENCY.value

    def __init__(self, fields: Sequence[str], *, weight: float = 1.0) -> None:
        self._fields = tuple(fields)
        self._weight = weight

    def assess(self, dataset: ProcessedDataset) -> QualityMeasurement:
        """Score type consistency per field across the dataset."""
        total = 0
        consistent = 0
        for name in self._fields:
            values = [
                record.value(name) for record in dataset.records if _is_present(record.value(name))
            ]
            if not values:
                continue
            types = [type(value).__name__ for value in values]
            dominant = max(set(types), key=types.count)
            total += len(values)
            consistent += sum(1 for type_name in types if type_name == dominant)
        score = 1.0 if total == 0 else consistent / total
        return _measure(
            QualityDimension.CONSISTENCY, score, self._weight, checked=total, consistent=consistent
        )


class UniquenessDimension:
    """Scores the fraction of records that are not duplicates.

    Duplication is judged by record identity, so it depends on how identity was
    assigned upstream -- a key field, or a content hash. A dataset of all-unique
    identities scores one.
    """

    dimension = QualityDimension.UNIQUENESS.value

    def __init__(self, *, weight: float = 1.0) -> None:
        self._weight = weight

    def assess(self, dataset: ProcessedDataset) -> QualityMeasurement:
        """Score uniqueness as the fraction of distinct record identities."""
        if not dataset.records:
            return _measure(QualityDimension.UNIQUENESS, 1.0, self._weight, records=0)
        identities = [record.identity for record in dataset.records]
        unique = len(set(identities))
        return _measure(
            QualityDimension.UNIQUENESS,
            unique / len(identities),
            self._weight,
            unique=unique,
            records=len(identities),
        )


class IntegrityDimension:
    """Scores the fraction of records whose key fields are all populated.

    Integrity here is the referential kind: a record missing a key that ties it
    to something else is an integrity gap. It differs from completeness in
    scoring records whole rather than individual values.
    """

    dimension = QualityDimension.INTEGRITY.value

    def __init__(self, key_fields: Sequence[str], *, weight: float = 1.0) -> None:
        self._keys = tuple(key_fields)
        self._weight = weight

    def assess(self, dataset: ProcessedDataset) -> QualityMeasurement:
        """Score integrity as the fraction of records with all keys present."""
        if not dataset.records or not self._keys:
            return _measure(QualityDimension.INTEGRITY, 1.0, self._weight, records=0)
        intact = sum(1 for record in dataset.records if self._has_all_keys(record))
        return _measure(
            QualityDimension.INTEGRITY,
            intact / len(dataset.records),
            self._weight,
            intact=intact,
            records=len(dataset.records),
        )

    def _has_all_keys(self, record: ProcessedRecord) -> bool:
        return all(_is_present(record.value(key)) for key in self._keys)


class TimelinessDimension:
    """Scores the fraction of records retrieved within a freshness window.

    A record retrieved no longer than ``max_age_seconds`` before the reference
    instant is timely. Records without a retrieval timestamp are treated as not
    timely, so missing provenance counts against the score rather than being
    silently ignored.
    """

    dimension = QualityDimension.TIMELINESS.value

    def __init__(self, reference: datetime, *, max_age_seconds: float, weight: float = 1.0) -> None:
        self._reference = reference
        self._max_age = max_age_seconds
        self._weight = weight

    def assess(self, dataset: ProcessedDataset) -> QualityMeasurement:
        """Score timeliness against the freshness window."""
        if not dataset.records:
            return _measure(QualityDimension.TIMELINESS, 1.0, self._weight, records=0)
        fresh = sum(1 for record in dataset.records if self._is_fresh(record))
        return _measure(
            QualityDimension.TIMELINESS,
            fresh / len(dataset.records),
            self._weight,
            fresh=fresh,
            records=len(dataset.records),
        )

    def _is_fresh(self, record: ProcessedRecord) -> bool:
        if record.retrieved_at is None:
            return False
        age = (self._reference - record.retrieved_at).total_seconds()
        return 0 <= age <= self._max_age


__all__ = [
    "AccuracyDimension",
    "CompletenessDimension",
    "ConsistencyDimension",
    "IntegrityDimension",
    "TimelinessDimension",
    "UniquenessDimension",
]
