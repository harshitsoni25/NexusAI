"""Backend-independent contracts for application-level state.

The application layer persists three kinds of long-lived state -- jobs,
checkpoints and schedules -- and, like every other capability in the framework,
it does so through ports rather than a concrete store. A :class:`JobStore` holds
jobs, a :class:`CheckpointStore` holds checkpoints, and a :class:`ScheduleStore`
holds schedules; each is satisfied by a SQLAlchemy adapter in infrastructure, and
the application neither knows nor cares which database is behind it.

A :class:`SiteAdapter` is a different kind of port: not storage, but a small,
site-specific bundle of configuration that teaches the generic engine how to
scrape one target, so that adding a site never means editing the core.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

from nexusai.domain.model.checkpoint import Checkpoint
from nexusai.domain.model.job import Job
from nexusai.domain.model.schedule import Schedule
from nexusai.shared.types import JsonValue


@runtime_checkable
class JobStore(Protocol):
    """Persists and retrieves jobs by identity."""

    def save(self, job: Job) -> None:
        """Persist a job, inserting or replacing by ``job_id``."""
        ...

    def get(self, job_id: str) -> Job | None:
        """Return the job with ``job_id``, or ``None`` if absent."""
        ...

    def list(self, *, limit: int = 100) -> Sequence[Job]:
        """Return recent jobs, newest first."""
        ...


@runtime_checkable
class CheckpointStore(Protocol):
    """Persists and retrieves checkpoints for a job."""

    def save(self, checkpoint: Checkpoint) -> None:
        """Persist a checkpoint. Writing must not corrupt the last valid one."""
        ...

    def latest(self, job_id: str) -> Checkpoint | None:
        """Return the most recent checkpoint for a job, or ``None``."""
        ...


@runtime_checkable
class ScheduleStore(Protocol):
    """Persists and retrieves schedules."""

    def save(self, schedule: Schedule) -> None:
        """Persist a schedule, inserting or replacing by ``schedule_id``."""
        ...

    def get(self, schedule_id: str) -> Schedule | None:
        """Return the schedule with ``schedule_id``, or ``None``."""
        ...

    def list(self) -> Sequence[Schedule]:
        """Return every schedule."""
        ...

    def delete(self, schedule_id: str) -> None:
        """Remove a schedule. Absent identity is a no-op."""
        ...


@runtime_checkable
class SiteAdapter(Protocol):
    """A small, site-specific bundle teaching the engine how to scrape one target.

    An adapter matches targets it handles, provides starting URLs and an
    extraction schema, and may express retrieval preferences and site-specific
    policy. It contains configuration, not engine code: adding a new site is a new
    adapter, never a change to the orchestrator or the engines.
    """

    @property
    def name(self) -> str:
        """A stable identifier for the adapter."""
        ...

    @property
    def version(self) -> str:
        """The adapter's version, recorded for resume compatibility."""
        ...

    def matches(self, target: str) -> bool:
        """Whether this adapter handles ``target``."""
        ...

    def start_urls(self, target: str) -> Sequence[str]:
        """Return the URLs to begin retrieval from for ``target``."""
        ...

    def extraction_schema(self) -> Mapping[str, JsonValue]:
        """Return the field-to-selector schema for extraction."""
        ...

    def preferences(self) -> Mapping[str, JsonValue]:
        """Return retrieval and policy preferences, such as a strategy hint."""
        ...
