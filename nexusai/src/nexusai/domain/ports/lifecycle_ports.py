"""Framework component contracts: Service and Factory.

These name capabilities the framework assembles and runs. Both are lifecycle
aware, because a service may hold resources and a factory-built component
certainly may. They are Protocols, so an implementation satisfies them
structurally without importing a base class from another layer (ADR-0003) --
which is what allows an infrastructure adapter to be a ``Service`` without
depending on the application layer that orchestrates it.
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from nexusai.domain.model.metadata import Metadata
from nexusai.shared.lifecycle import Disposable, Initializable

T_co = TypeVar("T_co", covariant=True)


@runtime_checkable
class Service(Initializable, Disposable, Protocol):
    """A unit of framework behaviour with a managed lifecycle.

    A service is created, initialised before use, and disposed when finished.
    The lifecycle methods are inherited from the shared protocols; a service that
    holds no resources simply implements them as no-ops, or mixes in
    ``LifecycleMixin`` to get that for free.
    """

    @property
    def name(self) -> str:
        """A stable identifier, used in logs, metrics and diagnostics."""
        ...


@runtime_checkable
class Factory(Protocol[T_co]):
    """Creates components of one kind on demand.

    A factory decouples *what* to create from *how* to create it: a caller asks
    for a component by name and receives a ready instance, without knowing which
    concrete class was chosen or how its dependencies were supplied. That
    indirection is what lets a new implementation be added by registration rather
    than by editing the factory (the Open/Closed Principle at the seam where
    components are born).
    """

    def create(self, name: str) -> T_co:
        """Create the component registered under ``name``.

        Raises:
            An implementation-defined framework error if no component is
            registered under that name.
        """
        ...

    def available(self) -> tuple[str, ...]:
        """Return the names this factory can create."""
        ...


@runtime_checkable
class Describable(Protocol):
    """A component that can describe itself with metadata.

    Optional across the framework. Where a component implements it, tooling --
    the ``plugins`` command, a report, a diagnostic -- can present it uniformly
    without special-casing each kind.
    """

    @property
    def metadata(self) -> Metadata:
        """Descriptive metadata for display and introspection."""
        ...
