"""Event dispatch infrastructure.

Holds the in-process bus that implements the publisher port. Event *types* are
defined in the domain; this package only delivers them.
"""

from __future__ import annotations

from nexusai.infrastructure.events.bus import InProcessEventBus, callback_subscriber

__all__ = ["InProcessEventBus", "callback_subscriber"]
