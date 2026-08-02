"""Tests for the change-detection domain models."""

from __future__ import annotations

from nexusai.domain.model.change import (
    ChangeSet,
    ChangeSummary,
    ChangeType,
    FieldDelta,
    RecordChange,
)


def _change(identity: str, kind: ChangeType) -> RecordChange:
    return RecordChange(identity=identity, change_type=kind)


def test_change_set_counts_by_type() -> None:
    change_set = ChangeSet(
        detector="d",
        changes=[
            _change("a", ChangeType.ADDED),
            _change("b", ChangeType.ADDED),
            _change("c", ChangeType.REMOVED),
            _change("d", ChangeType.MODIFIED),
        ],
    )
    assert change_set.added == 2
    assert change_set.removed == 1
    assert change_set.modified == 1
    assert change_set.has_changes is True


def test_empty_change_set_has_no_changes() -> None:
    assert ChangeSet(detector="d").has_changes is False


def test_record_change_serialises_with_deltas() -> None:
    change = RecordChange(
        identity="r1",
        change_type=ChangeType.MODIFIED,
        deltas=[FieldDelta(field="price", before=10, after=12)],
    )
    payload = change.to_dict()
    assert payload["change_type"] == "modified"
    assert payload["deltas"][0] == {"field": "price", "before": 10, "after": 12}


def test_change_set_serialises_with_rollup() -> None:
    change_set = ChangeSet(
        detector="content-hash",
        changes=[_change("a", ChangeType.ADDED)],
        attributes={"algo": "sha256"},
    )
    payload = change_set.to_dict()
    assert payload["detector"] == "content-hash"
    assert payload["added"] == 1
    assert payload["attributes"] == {"algo": "sha256"}


def test_summary_aggregates_change_sets() -> None:
    first = ChangeSet(detector="a", changes=[_change("x", ChangeType.ADDED)])
    second = ChangeSet(
        detector="b",
        changes=[_change("y", ChangeType.MODIFIED), _change("z", ChangeType.REMOVED)],
    )
    summary = ChangeSummary.from_change_sets([first, second])
    assert summary.added == 1
    assert summary.modified == 1
    assert summary.removed == 1
    assert summary.total == 3
    assert summary.detectors == ("a", "b")
    assert summary.to_dict()["total"] == 3
