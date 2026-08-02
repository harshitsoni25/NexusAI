"""Schedule management use cases: create, list, enable, disable, delete.

These coordinate the schedule store and the scheduler's next-run computation. A
created schedule has its first fire time computed and persisted; enabling or
disabling flips a flag; deleting removes it. Triggering due schedules is separate
(the scheduler decides due-ness and overlap; a scrape use case runs the job), so
these use cases never start work themselves.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime

from nexusai.application.scheduling.scheduler import next_run_after
from nexusai.domain.errors.exceptions import NexusAIError
from nexusai.domain.model.schedule import (
    OverlapPolicy,
    Schedule,
    ScheduleExpression,
)
from nexusai.domain.ports.application import ScheduleStore
from nexusai.domain.ports.observability import Clock, IdGenerator


class ScheduleUseCases:
    """Create and manage schedules through the schedule store."""

    def __init__(self, store: ScheduleStore, *, clock: Clock, ids: IdGenerator) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids

    def create(
        self,
        *,
        name: str,
        target: str,
        expression: ScheduleExpression,
        overlap_policy: OverlapPolicy = OverlapPolicy.SKIP,
        configuration_ref: str | None = None,
    ) -> Schedule:
        """Create and persist a schedule with its first run computed."""
        now = self._clock.now()
        schedule = Schedule(
            schedule_id=self._ids.new(),
            name=name,
            target=target,
            expression=expression,
            overlap_policy=overlap_policy,
            configuration_ref=configuration_ref,
            created_at=now,
            next_run=next_run_after(expression, now),
        )
        self._store.save(schedule)
        return schedule

    def list(self) -> Sequence[Schedule]:
        """Return every schedule."""
        return self._store.list()

    def set_enabled(self, schedule_id: str, *, enabled: bool) -> Schedule:
        """Enable or disable a schedule.

        Raises:
            NexusAIError: If no such schedule exists.
        """
        schedule = self._require(schedule_id)
        updated = replace(schedule, enabled=enabled)
        self._store.save(updated)
        return updated

    def delete(self, schedule_id: str) -> None:
        """Delete a schedule."""
        self._store.delete(schedule_id)

    def mark_run(self, schedule_id: str, *, at: datetime, result: str) -> Schedule:
        """Record that a schedule ran, advancing its next run."""
        schedule = self._require(schedule_id)
        updated = replace(
            schedule,
            last_run=at,
            last_result=result,
            next_run=next_run_after(schedule.expression, at),
        )
        self._store.save(updated)
        return updated

    def _require(self, schedule_id: str) -> Schedule:
        schedule = self._store.get(schedule_id)
        if schedule is None:
            raise NexusAIError("No such schedule", schedule_id=schedule_id)
        return schedule
