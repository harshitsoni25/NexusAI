"""Tests for the change-detection engine."""

from __future__ import annotations

from nexusai.application.processing.change import ChangeDetectionEngine
from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import (
    ProcessedDataset,
    ProcessedField,
    ProcessedRecord,
)
from nexusai.infrastructure.change.detectors import (
    FieldDiffDetector,
    RecordSetDetector,
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


def test_engine_runs_detectors_and_summarises() -> None:
    previous = ProcessedDataset(records=[_record("a", price=10), _record("b", price=1)])
    current = ProcessedDataset(records=[_record("a", price=15), _record("c", price=1)])
    engine = ChangeDetectionEngine([RecordSetDetector(), FieldDiffDetector()])
    change_sets, summary = engine.detect(current, previous)
    assert len(change_sets) == 2
    # Both detectors see the added "c" and removed "b"; field-diff also sees "a" modified.
    assert summary.added == 2
    assert summary.removed == 2
    assert summary.modified == 1
    assert "record-set" in summary.detectors


def test_engine_with_no_detectors() -> None:
    engine = ChangeDetectionEngine([])
    change_sets, summary = engine.detect(ProcessedDataset(), ProcessedDataset())
    assert change_sets == ()
    assert summary.total == 0
