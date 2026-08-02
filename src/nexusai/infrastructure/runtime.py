"""Adapters for the two ambient effects the domain refuses to reach for directly."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime


class SystemClock:
    """Real time, from the operating system.

    Wall-clock and monotonic time are separate methods because they answer
    different questions. ``now()`` records *when* something happened and may jump
    backwards when the system clock is adjusted; ``monotonic()`` measures *how
    long* something took and never does.
    """

    def now(self) -> datetime:
        """Return the current time as a timezone-aware UTC datetime."""
        return datetime.now(UTC)

    def monotonic(self) -> float:
        """Return a monotonically increasing counter, in seconds."""
        return time.monotonic()


class Uuid4IdGenerator:
    """Random identifiers, suitable for correlation and run identity."""

    def new(self) -> str:
        """Return a new UUID4 in canonical hyphenated form."""
        return str(uuid.uuid4())
