"""Models describing what changed between two versions of a dataset.

Change detection compares a current dataset against a previous snapshot and
reports what was added, removed or modified. These models are the vocabulary of
that report: they are structured for downstream reporting -- counts and
per-record deltas -- and carry no opinion about whether a change is good or bad.

The models are deliberately independent of how a change was detected. A
content-hash detector and a field-by-field detector both produce a
:class:`ChangeSet`; the consumer reads the same shape either way.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from nexusai.shared.types import JsonValue


class ChangeType(Enum):
    """How a record differs from its previous version."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldDelta:
    """A single field's change between two versions of a record.

    Attributes:
        field: The name of the field that changed.
        before: The previous value, or ``None`` if the field was added.
        after: The new value, or ``None`` if the field was removed.
    """

    field: str
    before: JsonValue = None
    after: JsonValue = None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {"field": self.field, "before": self.before, "after": self.after}


@dataclass(frozen=True, slots=True, kw_only=True)
class RecordChange:
    """The change affecting a single record, keyed by its identity.

    Attributes:
        identity: The stable key identifying the record across versions.
        change_type: Whether the record was added, removed or modified.
        deltas: The per-field changes, for a modified record.
    """

    identity: str
    change_type: ChangeType
    deltas: Sequence[FieldDelta] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "deltas", tuple(self.deltas))

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "identity": self.identity,
            "change_type": self.change_type.value,
            "deltas": [delta.to_dict() for delta in self.deltas],
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangeSet:
    """The complete set of changes a detector found between two datasets.

    Attributes:
        detector: The name of the detector that produced this set.
        changes: Every record-level change found. Unchanged records are omitted
            by convention, so an empty set means "nothing changed".
        attributes: Detector-specific supporting detail, such as the hashes that
            were compared for a content-hash detector.
    """

    detector: str
    changes: Sequence[RecordChange] = field(default_factory=tuple)
    attributes: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "changes", tuple(self.changes))
        object.__setattr__(self, "attributes", dict(self.attributes))

    def _count(self, change_type: ChangeType) -> int:
        return sum(1 for change in self.changes if change.change_type is change_type)

    @property
    def added(self) -> int:
        """How many records were added."""
        return self._count(ChangeType.ADDED)

    @property
    def removed(self) -> int:
        """How many records were removed."""
        return self._count(ChangeType.REMOVED)

    @property
    def modified(self) -> int:
        """How many records were modified."""
        return self._count(ChangeType.MODIFIED)

    @property
    def has_changes(self) -> bool:
        """Whether any change was found."""
        return bool(self.changes)

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation with roll-up counts."""
        return {
            "detector": self.detector,
            "added": self.added,
            "removed": self.removed,
            "modified": self.modified,
            "changes": [change.to_dict() for change in self.changes],
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangeSummary:
    """A roll-up of one or more change sets, for the processing context.

    Where a :class:`ChangeSet` is one detector's findings, a summary aggregates
    across detectors into the totals a report or a downstream consumer reads
    without walking every record.
    """

    added: int = 0
    removed: int = 0
    modified: int = 0
    detectors: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "detectors", tuple(self.detectors))

    @property
    def total(self) -> int:
        """The total number of changed records across all categories."""
        return self.added + self.removed + self.modified

    @classmethod
    def from_change_sets(cls, change_sets: Sequence[ChangeSet]) -> ChangeSummary:
        """Aggregate several change sets into one summary."""
        return cls(
            added=sum(change_set.added for change_set in change_sets),
            removed=sum(change_set.removed for change_set in change_sets),
            modified=sum(change_set.modified for change_set in change_sets),
            detectors=tuple(change_set.detector for change_set in change_sets),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "added": self.added,
            "removed": self.removed,
            "modified": self.modified,
            "total": self.total,
            "detectors": list(self.detectors),
        }
