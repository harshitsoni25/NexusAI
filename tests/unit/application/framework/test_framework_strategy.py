"""Tests for the StrategySelector."""

from __future__ import annotations

import pytest

from nexusai.application.framework.strategy import NoStrategyError, StrategySelector
from nexusai.domain.ports.strategy import Strategy
from nexusai.shared.registry import Registry


class Shout:
    name = "shout"

    def execute(self, request: str) -> str:
        return request.upper()

    def supports(self, request: str) -> bool:
        return isinstance(request, str) and request.startswith("!")


class Echo:
    name = "echo"

    def execute(self, request: str) -> str:
        return request


def _selector(*strategies: Strategy[str, str]) -> StrategySelector[str, str]:
    registry: Registry[Strategy[str, str]] = Registry("strategy")
    for strategy in strategies:
        registry.register(strategy.name, strategy)
    return StrategySelector(registry)


def test_by_name_returns_registered_strategy() -> None:
    selector = _selector(Shout(), Echo())
    assert selector.by_name("echo").execute("hi") == "hi"


def test_by_name_unknown_raises_no_strategy() -> None:
    selector = _selector(Echo())
    with pytest.raises(NoStrategyError, match="No strategy named 'missing'"):
        selector.by_name("missing")


def test_for_request_selects_first_supporting_conditional() -> None:
    selector = _selector(Shout(), Echo())
    assert selector.for_request("!hey").execute("!hey") == "!HEY"


def test_for_request_with_no_supporting_strategy_raises() -> None:
    selector = _selector(Shout())  # only supports '!' prefixed input
    with pytest.raises(NoStrategyError, match="No registered strategy supports"):
        selector.for_request("plain")


def test_for_request_ignores_non_conditional_strategies() -> None:
    # Echo is not a ConditionalStrategy, so it never matches by inspection.
    selector = _selector(Echo())
    with pytest.raises(NoStrategyError):
        selector.for_request("anything")


def test_resolve_prefers_explicit_name() -> None:
    selector = _selector(Shout(), Echo())
    # Even though '!x' would be handled by Shout via inspection, the name wins.
    assert selector.resolve("!x", name="echo").name == "echo"


def test_resolve_falls_back_to_inspection() -> None:
    selector = _selector(Shout(), Echo())
    assert selector.resolve("!x").name == "shout"
