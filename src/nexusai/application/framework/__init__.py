"""Reusable SDK building blocks for assembling and running framework components.

These are the mechanisms -- a component factory, a strategy selector, a lifecycle
manager, a service base, event-wiring helpers -- that later phases use to turn the
domain contracts into working systems. They combine contracts with the ambient
:class:`FrameworkContext` and the Phase 2 event bus, which is why they live in the
application layer rather than the domain: they orchestrate, they do not decide.

They are distinct from use cases. A use case is a business workflow; these are the
neutral machinery a use case is built from. Infrastructure adapters never import
this package -- they implement the domain contracts directly -- so the dependency
rule is preserved.
"""

from __future__ import annotations

from nexusai.application.framework.events import TypedSubscriber, subscribe
from nexusai.application.framework.factory import ComponentFactory, FactoryError
from nexusai.application.framework.lifecycle import LifecycleManager, managed_lifecycle
from nexusai.application.framework.service import BaseService, CompositeService
from nexusai.application.framework.strategy import StrategySelector

__all__ = [
    "BaseService",
    "ComponentFactory",
    "CompositeService",
    "FactoryError",
    "LifecycleManager",
    "StrategySelector",
    "TypedSubscriber",
    "managed_lifecycle",
    "subscribe",
]
