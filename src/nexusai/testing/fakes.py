"""Deterministic implementations of the framework's ambient ports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from nexusai.domain.events.base import DomainEvent
from nexusai.domain.model.plugin import ApiVersion, ExtensionPoint, PluginMetadata

EPOCH = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
"""Fixed starting point, so that assertions on timestamps can be exact."""


@dataclass(slots=True)
class FrozenClock:
    """A clock that only moves when told to.

    Wall-clock and monotonic time advance together, which keeps duration
    assertions readable while still exercising the two-method contract that the
    real clock implements.
    """

    instant: datetime = EPOCH
    elapsed: float = 0.0

    def now(self) -> datetime:
        """Return the frozen instant."""
        return self.instant

    def monotonic(self) -> float:
        """Return the accumulated elapsed seconds."""
        return self.elapsed

    def advance(self, seconds: float) -> None:
        """Move both clocks forward by ``seconds``."""
        self.instant += timedelta(seconds=seconds)
        self.elapsed += seconds


@dataclass(slots=True)
class SteppingClock:
    """A clock that advances a fixed step on each read.

    Where :class:`FrozenClock` stands still until told to move, this one moves on
    every read, so a component that measures elapsed time by subtracting a start
    instant from an end instant sees a stable, non-zero duration -- exactly what a
    retrieval provider needs to record a deterministic ``elapsed_seconds``.
    """

    step_seconds: float = 0.05
    instant: datetime = EPOCH

    def now(self) -> datetime:
        """Advance by the fixed step and return the new instant."""
        self.instant += timedelta(seconds=self.step_seconds)
        return self.instant

    def monotonic(self) -> float:
        """Return the elapsed seconds since the epoch."""
        return (self.instant - EPOCH).total_seconds()


@dataclass(slots=True)
class SequentialIdGenerator:
    """Predictable identifiers, so that generated ids can be asserted on."""

    prefix: str = "id"
    counter: int = 0

    def new(self) -> str:
        """Return the next identifier in sequence."""
        self.counter += 1
        return f"{self.prefix}-{self.counter:04d}"


@dataclass(frozen=True, slots=True)
class LogRecord:
    """One captured log call."""

    level: str
    message: str
    fields: Mapping[str, Any]


@dataclass(slots=True)
class RecordingLogger:
    """A logger that keeps everything it was asked to log.

    Satisfies the ``Logger`` port, so it can be injected anywhere the real logger
    goes and used to assert that a component reported what it claimed to report.
    """

    records: list[LogRecord] = field(default_factory=list)
    bound: Mapping[str, Any] = field(default_factory=dict)

    def bind(self, **fields: Any) -> RecordingLogger:
        """Return a logger sharing this one's record list, with extra fields."""
        return RecordingLogger(records=self.records, bound={**self.bound, **fields})

    def debug(self, message: str, /, **fields: Any) -> None:
        """Record a DEBUG call."""
        self._record("DEBUG", message, fields)

    def info(self, message: str, /, **fields: Any) -> None:
        """Record an INFO call."""
        self._record("INFO", message, fields)

    def warning(self, message: str, /, **fields: Any) -> None:
        """Record a WARNING call."""
        self._record("WARNING", message, fields)

    def error(self, message: str, /, **fields: Any) -> None:
        """Record an ERROR call."""
        self._record("ERROR", message, fields)

    def critical(self, message: str, /, **fields: Any) -> None:
        """Record a CRITICAL call."""
        self._record("CRITICAL", message, fields)

    def exception(self, message: str, /, **fields: Any) -> None:
        """Record an ERROR call and note that an exception was active."""
        self._record("ERROR", message, {**fields, "exception": True})

    def _record(self, level: str, message: str, fields: Mapping[str, Any]) -> None:
        self.records.append(LogRecord(level, message, {**self.bound, **fields}))

    def messages(self, level: str | None = None) -> Sequence[str]:
        """Return logged messages, optionally filtered by level."""
        return [r.message for r in self.records if level is None or r.level == level]

    def has_message(self, fragment: str, *, level: str | None = None) -> bool:
        """Whether any logged message contains ``fragment``."""
        return any(fragment in message for message in self.messages(level))


@dataclass(slots=True)
class RecordingSubscriber:
    """An event subscriber that stores what it receives.

    Args:
        event_types: Types to subscribe to.
        fail_with: When set, raise this on every event, to exercise the bus's
            failure isolation.
        delay_seconds: Advance a supplied clock by this much on each event, to
            exercise slow-subscriber reporting.
    """

    event_types: tuple[type[DomainEvent], ...] = (DomainEvent,)
    received: list[DomainEvent] = field(default_factory=list)
    fail_with: Exception | None = None
    delay_seconds: float = 0.0
    clock: FrozenClock | None = None
    label: str = "recording-subscriber"

    @property
    def handled_events(self) -> Sequence[type[DomainEvent]]:
        """Return the event types this subscriber was configured with."""
        return self.event_types

    def handle(self, event: DomainEvent) -> None:
        """Record the event, after applying any configured delay or failure."""
        if self.clock is not None and self.delay_seconds:
            self.clock.advance(self.delay_seconds)
        if self.fail_with is not None:
            raise self.fail_with
        self.received.append(event)


@dataclass(slots=True)
class StubPlugin:
    """A minimal plugin, for exercising discovery, registration and lifecycle."""

    name: str = "stub"
    extension_point: ExtensionPoint = ExtensionPoint.EXPORTER
    api_version: ApiVersion = field(default_factory=lambda: ApiVersion(1, 0))
    version: str = "1.0.0"
    initialised: bool = False
    disposed: bool = False
    fail_on_initialize: bool = False
    fail_on_dispose: bool = False

    @property
    def metadata(self) -> PluginMetadata:
        """Return the plugin's self-description."""
        return PluginMetadata(
            name=self.name,
            version=self.version,
            extension_point=self.extension_point,
            api_version=self.api_version,
            description="Test double",
            author="nexusai",
        )

    def initialize(self) -> None:
        """Mark the plugin as initialised, or fail if configured to."""
        if self.fail_on_initialize:
            raise RuntimeError(f"{self.name} refused to initialise")
        self.initialised = True

    def dispose(self) -> None:
        """Mark the plugin as disposed, or fail if configured to."""
        if self.fail_on_dispose:
            raise RuntimeError(f"{self.name} refused to dispose")
        self.disposed = True
