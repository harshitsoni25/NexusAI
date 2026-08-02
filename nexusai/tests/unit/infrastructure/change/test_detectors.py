"""Tests for the change detectors."""

from __future__ import annotations

from nexusai.domain.model.change import ChangeType
from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import (
    ProcessedDataset,
    ProcessedField,
    ProcessedRecord,
)
from nexusai.infrastructure.change.detectors import (
    ContentHashDetector,
    FieldDiffDetector,
    RecordSetDetector,
    StructuralDetector,
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


def _dataset(*records: ProcessedRecord) -> ProcessedDataset:
    return ProcessedDataset(records=records)


def test_record_set_detects_membership() -> None:
    previous = _dataset(_record("a"), _record("b"))
    current = _dataset(_record("a"), _record("c"))
    change_set = RecordSetDetector().detect(current, previous)
    assert change_set.added == 1
    assert change_set.removed == 1
    assert change_set.modified == 0


def test_content_hash_detects_modification() -> None:
    previous = _dataset(_record("a", price=10))
    current = _dataset(_record("a", price=15))
    change_set = ContentHashDetector().detect(current, previous)
    assert change_set.modified == 1


def test_content_hash_ignores_unchanged() -> None:
    same = _dataset(_record("a", price=10))
    assert ContentHashDetector().detect(same, same).has_changes is False


def test_field_diff_reports_deltas() -> None:
    previous = _dataset(_record("a", price=10, name="X"))
    current = _dataset(_record("a", price=15, name="X"))
    change_set = FieldDiffDetector().detect(current, previous)
    modified = [c for c in change_set.changes if c.change_type is ChangeType.MODIFIED]
    assert len(modified) == 1
    deltas = modified[0].deltas
    assert len(deltas) == 1
    assert deltas[0].field == "price"
    assert deltas[0].before == 10
    assert deltas[0].after == 15


def test_field_diff_reports_added_removed() -> None:
    previous = _dataset(_record("a", x=1), _record("gone", x=1))
    current = _dataset(_record("a", x=1), _record("new", x=1))
    change_set = FieldDiffDetector().detect(current, previous)
    assert change_set.added == 1
    assert change_set.removed == 1


def test_structural_detects_shape_change() -> None:
    previous = _dataset(_record("a", name="X"))
    current = _dataset(_record("a", name="X", price=1))
    change_set = StructuralDetector().detect(current, previous)
    assert change_set.modified == 1
    assert change_set.attributes["compares"] == "field-structure"


def test_structural_ignores_value_only_change() -> None:
    previous = _dataset(_record("a", name="X"))
    current = _dataset(_record("a", name="Y"))
    assert StructuralDetector().detect(current, previous).has_changes is False
