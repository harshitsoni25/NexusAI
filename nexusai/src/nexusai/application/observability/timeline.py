"""A thread-safe recorder that assembles an execution timeline.

The recorder collects :class:`TimelineEvent` values as a run proceeds -- job
started, stage completed, checkpoint written, export produced -- and hands back an
immutable :class:`Timeline` when asked. It records only bounded labels and
attributes, never payloads, and it is safe to record into from several threads,
since concurrent jobs may share one recorder. It has no dependency on reporting:
reporting reads the timeline, not the other way round.
"""

from __future__ import annotations

import threading
from datetime import datetime

from nexusai.domain.observability.timeline import (
    Timeline,
    TimelineEvent,
    TimelineEventType,
)
from nexusai.domain.ports.observability import Clock


class TimelineRecorder:
    """Collects timeline events for one run, safely across threads."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._events: list[TimelineEvent] = []
        self._lock = threading.Lock()

    def record(
        self,
        event_type: TimelineEventType,
        *,
        label: str = "",
        occurred_at: datetime | None = None,
        **attributes: str | int | float,
    ) -> None:
        """Append an event to the timeline."""
        event = TimelineEvent(
            event_type=event_type,
            occurred_at=occurred_at or self._clock.now(),
            label=label,
            attributes=attributes,
        )
        with self._lock:
            self._events.append(event)

    def timeline(self) -> Timeline:
        """Return an immutable snapshot of the events recorded so far."""
        with self._lock:
            return Timeline(events=tuple(self._events))
