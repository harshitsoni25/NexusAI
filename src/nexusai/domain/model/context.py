"""The ambient context handed to framework components.

``FrameworkContext`` bundles the cross-cutting collaborators a component needs --
a logger, a metrics sink, a clock, an identifier generator, the correlation id
and a snapshot of configuration -- into one immutable object passed at
construction.

It exists so that a component's constructor does not grow a parameter per
cross-cutting concern, and so that deriving a narrowed context for a nested unit
of work is a single call rather than a manual re-threading of six collaborators.

It holds only *ports* and immutable data, so it stays within the domain: no
concrete logger, no Pydantic settings, nothing technology-specific.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from nexusai.domain.model.execution import ConfigurationSnapshot
from nexusai.domain.ports.observability import Clock, IdGenerator, Logger, MetricsSink
from nexusai.shared.identifiers import CorrelationId


@dataclass(frozen=True, slots=True, kw_only=True)
class FrameworkContext:
    """Cross-cutting collaborators shared by framework components.

    Attributes:
        logger: Structured logger, already bound with ambient fields.
        metrics: Destination for operational metrics.
        clock: Source of time.
        id_generator: Source of unique identifiers.
        correlation_id: Identity tying this scope's telemetry together.
        configuration: Immutable view of effective configuration.
    """

    logger: Logger
    metrics: MetricsSink
    clock: Clock
    id_generator: IdGenerator
    correlation_id: CorrelationId
    configuration: ConfigurationSnapshot

    def for_component(self, component: str, **fields: Any) -> FrameworkContext:
        """Return a context whose logger is bound to ``component``.

        A component receives a context already carrying its own name in every log
        line, so it never has to remember to add it. The rest of the context is
        shared unchanged.
        """
        bound = self.logger.bind(component=component, **fields)
        return replace(self, logger=bound)

    def nested(self, correlation_id: CorrelationId) -> FrameworkContext:
        """Return a context for a nested unit of work under ``correlation_id``.

        The new correlation id is also bound into the logger, so telemetry from
        the nested scope is attributed to it without any further wiring.
        """
        bound = self.logger.bind(correlation_id=str(correlation_id))
        return replace(self, correlation_id=correlation_id, logger=bound)

    def new_correlation_id(self) -> CorrelationId:
        """Mint a fresh correlation id from the injected generator."""
        return CorrelationId(self.id_generator.new())
