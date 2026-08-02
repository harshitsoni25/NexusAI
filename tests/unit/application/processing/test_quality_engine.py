"""Tests for the quality engine."""

from __future__ import annotations

from nexusai.application.processing.quality import QualityEngine
from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import (
    ProcessedDataset,
    ProcessedField,
    ProcessedRecord,
)
from nexusai.domain.model.quality import QualityGrade
from nexusai.domain.policy.quality_scoring import QualityScorer
from nexusai.infrastructure.quality.dimensions import (
    CompletenessDimension,
    UniquenessDimension,
)
from nexusai.shared.types import JsonValue


def _record(identity: str, **fields: JsonValue) -> ProcessedRecord:
    return ProcessedRecord(
        identity=identity,
        raw=ExtractionResult(),
        fields={
            name: ProcessedField(name=name, value=value, raw_value=value)
            for name, value in fields.items()
        },
    )


def test_engine_scores_and_grades() -> None:
    dataset = ProcessedDataset(
        records=[_record("a", name="X", price=1), _record("b", name="Y", price=2)]
    )
    engine = QualityEngine([CompletenessDimension(["name", "price"]), UniquenessDimension()])
    result, grade = engine.assess(dataset)
    assert result.composite_score == 1.0
    assert grade is QualityGrade.A


def test_engine_uses_supplied_scorer() -> None:
    dataset = ProcessedDataset(records=[_record("a", name="X"), _record("a", name="X")])
    strict = QualityScorer(bands=((0.99, QualityGrade.A),))
    engine = QualityEngine([UniquenessDimension()], scorer=strict)
    _result, grade = engine.assess(dataset)
    # Uniqueness is 0.5, below the 0.99 band, so it falls to F.
    assert grade is QualityGrade.F
