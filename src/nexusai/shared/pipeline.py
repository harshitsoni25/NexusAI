"""A generic middleware pipeline.

A pipeline threads a mutable context object through an ordered chain of
middleware. Each middleware may inspect or modify the context, do work before
and after the rest of the chain, short-circuit by not calling forward, or wrap
the continuation in a try/finally. This is the Chain of Responsibility, and it
is the reusable substance behind every "cross-cutting concerns around a core
operation" requirement in the specification.

It is pure and technology-agnostic on purpose. The HTTP request chain, an
extraction pipeline and a future export pipeline all reuse this one mechanism
rather than each growing its own. Because it lives in ``shared``, infrastructure
and application can both use it without depending on one another.

The pipeline expresses composition over inheritance directly: behaviour is added
by placing an object in the chain, never by subclassing a base with hook
methods.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol, TypeVar, runtime_checkable

C = TypeVar("C")

Next = Callable[[C], None]
"""Continuation invoked to pass control to the rest of the chain."""


@runtime_checkable
class Middleware(Protocol[C]):
    """One link in a pipeline.

    An implementation does its "before" work, calls ``call_next(context)`` to
    invoke the rest of the chain, then does its "after" work. Omitting the
    ``call_next`` call short-circuits the pipeline -- a legitimate and useful
    thing to do, for a cache hit or a rejected request.
    """

    def process(self, context: C, call_next: Next[C]) -> None:
        """Handle ``context``, optionally invoking ``call_next`` to continue."""
        ...


class Pipeline[C]:
    """An ordered, immutable chain of middleware over a context type.

    A pipeline is built once and run many times. It is deliberately immutable:
    ``then`` returns a new pipeline rather than mutating this one, so a pipeline
    shared between runs cannot be reconfigured underneath one of them.

    Args:
        middleware: The chain, outermost first. The first entry sees the context
            before every later entry and, if it wraps ``call_next``, after them.
    """

    __slots__ = ("_middleware",)

    def __init__(self, middleware: Sequence[Middleware[C]] = ()) -> None:
        self._middleware: tuple[Middleware[C], ...] = tuple(middleware)

    def then(self, middleware: Middleware[C]) -> Pipeline[C]:
        """Return a new pipeline with ``middleware`` appended as the innermost."""
        return Pipeline([*self._middleware, middleware])

    def prepend(self, middleware: Middleware[C]) -> Pipeline[C]:
        """Return a new pipeline with ``middleware`` added as the outermost."""
        return Pipeline([middleware, *self._middleware])

    def __len__(self) -> int:
        return len(self._middleware)

    def run(self, context: C, terminal: Next[C] | None = None) -> C:
        """Thread ``context`` through the chain and return it.

        Args:
            context: The mutable object passed to each middleware.
            terminal: The innermost action, invoked after every middleware has
                delegated forward. Defaults to doing nothing, which is what makes
                a pipeline of pure observers valid on its own.

        Returns:
            The same context object, after the chain has run. Returned for
            convenience; the object is mutated in place.
        """
        end: Next[C] = terminal if terminal is not None else _noop

        def link(index: int) -> Next[C]:
            if index >= len(self._middleware):
                return end
            middleware = self._middleware[index]

            def call(ctx: C) -> None:
                middleware.process(ctx, link(index + 1))

            return call

        link(0)(context)
        return context


def _noop[C](_: C) -> None:
    """Default terminal action: do nothing."""
