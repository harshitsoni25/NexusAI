"""Adapters: every implementation that touches the outside world.

Implements the ports declared by ``domain`` and translates third-party
exceptions into the framework hierarchy at its own boundary, so that no
``httpx``, ``playwright`` or ``sqlalchemy`` exception ever propagates inward.

May import ``domain`` and ``shared``. Must never import ``application`` or
``presentation``: an adapter does not know which use case invoked it.
"""

from __future__ import annotations
