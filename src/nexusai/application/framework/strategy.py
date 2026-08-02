"""Selection among registered strategies.

Two ways to choose, matching the two ways strategies declare their applicability.
Selection by *name* is explicit: configuration names the strategy and the selector
returns it. Selection by *inspection* walks conditional strategies and returns the
first that declares it supports the input.

Detection and decision stay separate: the selector chooses, the strategy executes.
A strategy therefore never has to know why it was chosen, and the choosing logic
lives in one place rather than being scattered through the strategies themselves.
"""

from __future__ import annotations

from dataclasses import dataclass

from nexusai.domain.ports.strategy import ConditionalStrategy, Strategy
from nexusai.shared.registry import Registry, RegistryError


class NoStrategyError(Exception):
    """Raised when no registered strategy applies.

    A plain exception at this layer, translated at the boundary. Its message
    names the strategies that were considered, because the usual cause is either
    a misconfigured name or an input none of them recognises.
    """


@dataclass(slots=True)
class StrategySelector[In, Out]:
    """Chooses a strategy by name or by inspecting the input.

    Args:
        registry: The strategies to choose among, keyed by name.
    """

    registry: Registry[Strategy[In, Out]]

    def by_name(self, name: str) -> Strategy[In, Out]:
        """Return the strategy registered under ``name``.

        Raises:
            NoStrategyError: If no strategy is registered under that name.
        """
        try:
            return self.registry.get(name)
        except RegistryError as exc:
            raise NoStrategyError(str(exc)) from exc

    def for_request(self, request: In) -> Strategy[In, Out]:
        """Return the first registered strategy that supports ``request``.

        Only strategies implementing :class:`ConditionalStrategy` participate; a
        strategy that cannot declare its applicability cannot be chosen by
        inspection and must be selected by name.

        Raises:
            NoStrategyError: If no strategy declares support for the request.
        """
        for strategy in self.registry:
            if isinstance(strategy, ConditionalStrategy) and strategy.supports(request):
                return strategy
        raise NoStrategyError(
            f"No registered strategy supports the request "
            f"(considered: {', '.join(self.registry.names()) or 'none'})"
        )

    def resolve(self, request: In, *, name: str | None = None) -> Strategy[In, Out]:
        """Select by ``name`` when given, otherwise by inspecting ``request``.

        This is the precedence an explicit configuration override expects: a named
        strategy always wins, and inspection is the fallback when nothing was
        named.
        """
        return self.by_name(name) if name is not None else self.for_request(request)
