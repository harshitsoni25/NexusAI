"""Test doubles shipped with the framework.

These are part of the distribution rather than the test suite because plugin
authors need them too: writing a well-tested exporter should not require
reimplementing a fake clock and a recording logger first.

Every double here is a *fake* -- a real, working implementation with a simplified
backing store -- rather than a mock. Fakes exercise the same code paths a real
adapter would and do not need to be rewritten when an implementation changes.
"""

from __future__ import annotations

from nexusai.testing.fakes import (
    FrozenClock,
    LogRecord,
    RecordingLogger,
    RecordingSubscriber,
    SequentialIdGenerator,
    SteppingClock,
    StubPlugin,
)

__all__ = [
    "FrozenClock",
    "LogRecord",
    "RecordingLogger",
    "RecordingSubscriber",
    "SequentialIdGenerator",
    "SteppingClock",
    "StubPlugin",
]
