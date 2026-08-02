"""The execution timeline: a structured, ordered record of what happened.

A timeline is a sequence of typed events -- job created, stage started, checkpoint
written, export produced, completion -- each with a timestamp and a small,
bounded set of attributes. It is assembled from events the framework already
emits, carries no high-cardinality payloads, and is a pure value: reporting
consumes it, and the timeline never depends on a report renderer.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TimelineEventType(Enum):
    """The kinds of event a timeline records."""

    JOB_CREATED = "job.created"
    JOB_QUEUED = "job.queued"
    JOB_STARTED = "job.started"
    STAGE_STARTED = "stage.started"
    STAGE_COMPLETED = "stage.completed"
    STAGE_SKIPPED = "stage.skipped"
    RETRY = "retry"
    WARNING = "warning"
    CHECKPOINT = "checkpoint"
    EXPORT = "export"
    REPORT = "report"
    FAILURE = "failure"
    CANCELLATION = "cancellation"
    COMPLETION = "completion"


@dataclass(frozen=True, slots=True, kw_only=True)
class TimelineEvent:
    """One event on the execution timeline.

    Attributes:
        event_type: What kind of event this is.
        occurred_at: When it happened.
        label: A short, bounded label (a stage name, a format), never a payload.
        attributes: A small map of bounded attributes.
    """

    event_type: TimelineEventType
    occurred_at: datetime
    label: str = ""
    attributes: Mapping[str, str | int | float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", dict(self.attributes))

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {
            "event_type": self.event_type.value,
            "occurred_at": self.occurred_at.isoformat(),
            "label": self.label,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class Timeline:
    """An ordered collection of timeline events for one job or run."""

    events: Sequence[TimelineEvent] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "events", tuple(self.events))

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {"events": [event.to_dict() for event in self.events]}
