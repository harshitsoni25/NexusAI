"""The real clock and identifier generator."""

from __future__ import annotations

from datetime import UTC

from nexusai.infrastructure.runtime import SystemClock, Uuid4IdGenerator


def test_the_clock_reports_timezone_aware_utc() -> None:
    # A naive timestamp cannot be compared across machines, which makes it
    # useless for correlating a distributed run.
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() == UTC.utcoffset(None)


def test_monotonic_time_never_moves_backwards() -> None:
    clock = SystemClock()
    first = clock.monotonic()
    assert clock.monotonic() >= first


def test_identifiers_are_unique() -> None:
    generator = Uuid4IdGenerator()
    assert len({generator.new() for _ in range(100)}) == 100


def test_identifiers_are_canonical_uuids() -> None:
    from uuid import UUID

    assert str(UUID(Uuid4IdGenerator().new()))
