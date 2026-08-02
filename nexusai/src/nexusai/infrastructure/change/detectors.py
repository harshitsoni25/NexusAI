"""Change detectors comparing a current dataset against a previous one.

Each detector owns one notion of what "changed" means and reports it as a
:class:`ChangeSet`. A record-set detector answers "which records appeared or
vanished?"; a field-diff detector answers "which values moved?"; a content-hash
detector answers "did this record change at all?"; a structural detector answers
"did the shape of the document change?". A consumer picks the detectors whose
notion of change matters to it, and reads the uniform result.

Detectors are stateless and deterministic: the previous dataset is always passed
in, so the same pair of datasets always yields the same change set.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from nexusai.domain.model.change import (
    ChangeSet,
    ChangeType,
    FieldDelta,
    RecordChange,
)
from nexusai.domain.model.processing import ProcessedDataset, ProcessedRecord
from nexusai.shared.types import JsonValue


def _by_identity(dataset: ProcessedDataset) -> Mapping[str, ProcessedRecord]:
    return {record.identity: record for record in dataset.records}


def _record_hash(record: ProcessedRecord) -> str:
    payload = json.dumps(dict(record.values()), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RecordSetDetector:
    """Reports records added to and removed from the dataset by identity.

    The membership view of change: it does not look inside records, only at which
    identities are present now versus before. Pair it with a field-diff detector
    to also see modifications.
    """

    name = "record-set"

    def detect(self, current: ProcessedDataset, previous: ProcessedDataset) -> ChangeSet:
        """Report added and removed records by identity."""
        now = _by_identity(current)
        before = _by_identity(previous)
        changes = [
            RecordChange(identity=identity, change_type=ChangeType.ADDED)
            for identity in now
            if identity not in before
        ]
        changes.extend(
            RecordChange(identity=identity, change_type=ChangeType.REMOVED)
            for identity in before
            if identity not in now
        )
        return ChangeSet(detector=self.name, changes=changes)


class ContentHashDetector:
    """Reports records whose content hash changed between versions.

    The cheapest modification check: it hashes each record's values and compares,
    flagging a modification without saying which field moved. Also reports
    additions and removals, so it can stand alone as a coarse detector.
    """

    name = "content-hash"

    def detect(self, current: ProcessedDataset, previous: ProcessedDataset) -> ChangeSet:
        """Report added, removed and content-changed records."""
        now = _by_identity(current)
        before = _by_identity(previous)
        changes: list[RecordChange] = []
        for identity, record in now.items():
            if identity not in before:
                changes.append(RecordChange(identity=identity, change_type=ChangeType.ADDED))
            elif _record_hash(record) != _record_hash(before[identity]):
                changes.append(RecordChange(identity=identity, change_type=ChangeType.MODIFIED))
        changes.extend(
            RecordChange(identity=identity, change_type=ChangeType.REMOVED)
            for identity in before
            if identity not in now
        )
        return ChangeSet(detector=self.name, changes=changes)


class FieldDiffDetector:
    """Reports modified records with the specific field values that changed.

    The detailed modification view: for each record present in both datasets, it
    compares field values and records a :class:`FieldDelta` for every difference,
    so a report can show exactly what moved. Additions and removals are reported
    too, without deltas.
    """

    name = "field-diff"

    def detect(self, current: ProcessedDataset, previous: ProcessedDataset) -> ChangeSet:
        """Report per-field modifications alongside additions and removals."""
        now = _by_identity(current)
        before = _by_identity(previous)
        changes: list[RecordChange] = []
        for identity, record in now.items():
            if identity not in before:
                changes.append(RecordChange(identity=identity, change_type=ChangeType.ADDED))
                continue
            deltas = _field_deltas(record.values(), before[identity].values())
            if deltas:
                changes.append(
                    RecordChange(identity=identity, change_type=ChangeType.MODIFIED, deltas=deltas)
                )
        changes.extend(
            RecordChange(identity=identity, change_type=ChangeType.REMOVED)
            for identity in before
            if identity not in now
        )
        return ChangeSet(detector=self.name, changes=changes)


class StructuralDetector:
    """Reports records whose document structure changed.

    Where the other detectors compare extracted values, this compares the *shape*
    of the source: the set of field names present. It catches a page whose layout
    changed even when the values happen to match -- the early warning that a
    scraper's selectors may be about to break.
    """

    name = "structural"

    def detect(self, current: ProcessedDataset, previous: ProcessedDataset) -> ChangeSet:
        """Report records whose set of populated field names changed."""
        now = _by_identity(current)
        before = _by_identity(previous)
        changes: list[RecordChange] = []
        for identity, record in now.items():
            if identity not in before:
                continue
            current_shape = frozenset(record.values())
            previous_shape = frozenset(before[identity].values())
            if current_shape != previous_shape:
                added = sorted(current_shape - previous_shape)
                removed = sorted(previous_shape - current_shape)
                changes.append(
                    RecordChange(
                        identity=identity,
                        change_type=ChangeType.MODIFIED,
                        deltas=[FieldDelta(field=name, after="present") for name in added]
                        + [FieldDelta(field=name, before="present") for name in removed],
                    )
                )
        return ChangeSet(
            detector=self.name,
            changes=changes,
            attributes={"compares": "field-structure"},
        )


def _field_deltas(
    current: Mapping[str, JsonValue], previous: Mapping[str, JsonValue]
) -> list[FieldDelta]:
    names = set(current) | set(previous)
    deltas: list[FieldDelta] = []
    for name in sorted(names):
        before_value = previous.get(name)
        after_value = current.get(name)
        if before_value != after_value:
            deltas.append(FieldDelta(field=name, before=before_value, after=after_value))
    return deltas


__all__ = [
    "ContentHashDetector",
    "FieldDiffDetector",
    "RecordSetDetector",
    "StructuralDetector",
]
