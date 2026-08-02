"""Tests for the generic middleware pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

from nexusai.shared.pipeline import Middleware, Next, Pipeline


@dataclass
class Ctx:
    """A mutable context accumulating a trace of what ran."""

    trace: list[str] = field(default_factory=list)
    stop: bool = False


class Record:
    """Middleware that records before/after around the continuation."""

    def __init__(self, label: str) -> None:
        self.label = label

    def process(self, context: Ctx, call_next: Next[Ctx]) -> None:
        context.trace.append(f"{self.label}:before")
        call_next(context)
        context.trace.append(f"{self.label}:after")


class ShortCircuit:
    """Middleware that stops the chain without delegating forward."""

    def process(self, context: Ctx, call_next: Next[Ctx]) -> None:
        context.trace.append("short")
        # Deliberately does not call call_next.


def test_empty_pipeline_runs_terminal_only() -> None:
    ctx = Pipeline[Ctx]().run(Ctx(), terminal=lambda c: c.trace.append("terminal"))
    assert ctx.trace == ["terminal"]


def test_empty_pipeline_without_terminal_is_valid() -> None:
    ctx = Pipeline[Ctx]().run(Ctx())
    assert ctx.trace == []


def test_nesting_order_is_onion() -> None:
    pipeline = Pipeline([Record("a"), Record("b")])
    ctx = pipeline.run(Ctx(), terminal=lambda c: c.trace.append("core"))
    assert ctx.trace == ["a:before", "b:before", "core", "b:after", "a:after"]


def test_short_circuit_skips_inner_and_terminal() -> None:
    pipeline: Pipeline[Ctx] = Pipeline([Record("a"), ShortCircuit(), Record("b")])
    ctx = pipeline.run(Ctx(), terminal=lambda c: c.trace.append("core"))
    assert ctx.trace == ["a:before", "short", "a:after"]


def test_then_appends_as_innermost_and_is_immutable() -> None:
    base = Pipeline([Record("a")])
    extended = base.then(Record("b"))
    assert len(base) == 1
    assert len(extended) == 2
    ctx = extended.run(Ctx())
    assert ctx.trace == ["a:before", "b:before", "b:after", "a:after"]


def test_prepend_adds_as_outermost() -> None:
    pipeline = Pipeline([Record("inner")]).prepend(Record("outer"))
    ctx = pipeline.run(Ctx())
    assert ctx.trace[0] == "outer:before"
    assert ctx.trace[-1] == "outer:after"


def test_run_returns_same_context_object() -> None:
    original = Ctx()
    returned = Pipeline[Ctx]().run(original)
    assert returned is original


def test_middleware_protocol_is_satisfied_structurally() -> None:
    assert isinstance(Record("x"), Middleware)
