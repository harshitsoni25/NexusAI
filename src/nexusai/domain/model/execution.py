"""Reusable descriptions of an execution and its effective configuration.

These are generic framework models, not workflow objects. ``ExecutionInfo``
records the identity and timing of *some* unit of framework work without knowing
whether it is a scrape, an export or a report -- deliberately, because the same
shape must serve all of them. Job and Task, which carry workflow semantics,
belong to a later phase and are explicitly not defined here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from nexusai.shared.identifiers import CorrelationId
from nexusai.shared.types import JsonMapping, JsonValue


class ExecutionStatus(Enum):
    """The coarse outcome state of a unit of framework work."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        """Whether no further transition is expected from this state."""
        return self in {
            ExecutionStatus.SUCCEEDED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionInfo:
    """Identity, timing and outcome of a unit of framework work.

    Immutable: a state transition produces a new instance through the helper
    methods rather than mutating this one, so a reference captured for reporting
    reflects the state at the moment it was captured.

    Attributes:
        correlation_id: Ties this execution to its logs, metrics and events.
        started_at: When work began, if it has.
        finished_at: When work ended, if it has.
        status: The current coarse state.
        attributes: Free-form detail a caller attaches, such as what was executed.
    """

    correlation_id: CorrelationId
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    attributes: JsonMapping = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", dict(self.attributes))

    @property
    def duration_seconds(self) -> float | None:
        """Elapsed wall-clock seconds, or ``None`` if not both timestamps exist."""
        if self.started_at is None or self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    def started(self, when: datetime) -> ExecutionInfo:
        """Return a copy marked running, started at ``when``."""
        return self._replace(status=ExecutionStatus.RUNNING, started_at=when)

    def finished(self, status: ExecutionStatus, when: datetime) -> ExecutionInfo:
        """Return a copy marked with a terminal ``status``, finished at ``when``.

        Raises:
            ValueError: If ``status`` is not a terminal state.
        """
        if not status.is_terminal:
            raise ValueError(f"{status} is not a terminal status")
        return self._replace(status=status, finished_at=when)

    def with_attributes(self, **updates: JsonValue) -> ExecutionInfo:
        """Return a copy with ``updates`` merged into the attributes."""
        return self._replace(attributes={**self.attributes, **updates})

    def _replace(self, **changes: Any) -> ExecutionInfo:
        current: dict[str, Any] = {
            "correlation_id": self.correlation_id,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "attributes": dict(self.attributes),
        }
        current.update(changes)
        return ExecutionInfo(**current)

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "correlation_id": str(self.correlation_id),
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True, slots=True)
class ConfigurationSnapshot:
    """An immutable, infrastructure-independent view of effective configuration.

    The loader and its Pydantic settings live in infrastructure. This snapshot is
    the domain-facing shape: effective values as plain JSON data, plus the origin
    of each key. It exists so that a use case, a report or an audit record can
    read "what configuration did this execution run under, and where did each
    value come from?" without importing Pydantic and without the settings being
    mutable (ADR-0004).

    Recording the snapshot against an execution is what keeps a run reproducible
    after the configuration file has changed.

    Attributes:
        values: The effective configuration as nested JSON data.
        origins: Dotted key to the name of the source that supplied it.
    """

    values: JsonMapping = field(default_factory=dict)
    origins: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", dict(self.values))
        object.__setattr__(self, "origins", dict(self.origins))

    def origin_of(self, dotted_key: str) -> str | None:
        """Return the source that supplied ``dotted_key``, if recorded."""
        return self.origins.get(dotted_key)

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {"values": dict(self.values), "origins": dict(self.origins)}
