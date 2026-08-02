"""A registry-backed component factory.

The factory resolves a component by name from a registry of *builders* and calls
the chosen builder with the ambient context, so that every component is created
the same way and receives its cross-cutting collaborators without the call site
assembling them by hand. Adding a component is a registration, never an edit to
the factory -- the Open/Closed Principle at the point where components are born.

Builders rather than classes are registered so that a component with constructor
dependencies beyond the context can be expressed as a small closure, and so the
factory need not know any concrete class.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from nexusai.domain.model.context import FrameworkContext
from nexusai.shared.registry import Registry, RegistryError

type Builder[T] = Callable[[FrameworkContext], T]
"""A callable that builds a component from the ambient context."""


class FactoryError(Exception):
    """Raised when a component cannot be created.

    A plain exception at this layer; callers translate it into the framework
    hierarchy at the boundary where it matters. Kept separate from
    ``RegistryError`` so that "no such component" and "the builder failed" remain
    distinguishable.
    """


@dataclass(slots=True)
class ComponentFactory[T]:
    """Creates components from registered builders, injecting the context.

    Args:
        context: The ambient context handed to every builder.
        registry: The registry of builders. A fresh, labelled registry is created
            when none is supplied.
    """

    context: FrameworkContext
    registry: Registry[Builder[T]]

    def __init__(
        self, context: FrameworkContext, registry: Registry[Builder[T]] | None = None
    ) -> None:
        self.context = context
        self.registry = registry if registry is not None else Registry("component builder")

    def register(self, name: str, builder: Builder[T], *, replace: bool = False) -> None:
        """Register ``builder`` under ``name``."""
        self.registry.register(name, builder, replace=replace)

    def create(self, name: str) -> T:
        """Create the component registered under ``name``.

        Raises:
            FactoryError: If nothing is registered under ``name``, or the builder
                raises while constructing the component. The two causes carry
                different messages so the failure can be told apart.
        """
        try:
            builder = self.registry.get(name)
        except RegistryError as exc:
            raise FactoryError(str(exc)) from exc
        try:
            return builder(self.context)
        except Exception as exc:
            raise FactoryError(
                f"The builder for {name!r} failed: {type(exc).__name__}: {exc}"
            ) from exc

    def available(self) -> tuple[str, ...]:
        """Return the names this factory can create."""
        return self.registry.names()

    def freeze(self) -> None:
        """Close the underlying registry to further registration."""
        self.registry.freeze()
