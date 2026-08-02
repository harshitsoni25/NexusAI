"""Domain event definitions.

The generic event base and a small set of framework-lifecycle events. Business
events -- page acquired, record extracted, run completed -- are introduced by the
phases that own the components emitting them, so that an event and its producer
arrive together.
"""

from __future__ import annotations

from nexusai.domain.events.base import (
    ComponentDisposed,
    ComponentInitialized,
    DomainEvent,
    FrameworkStarted,
)

__all__ = [
    "ComponentDisposed",
    "ComponentInitialized",
    "DomainEvent",
    "FrameworkStarted",
]
