"""A typed, name-keyed registry.

The framework registers interchangeable components -- strategies, validators,
exporters -- and looks them up by name at assembly time. This is the one place
that behaviour lives, so a registry is not reimplemented per component kind.

State here is instance-scoped and explicitly passed, never global. A registry
can be frozen once populated, which is what stops the registered set changing
mid-run: if it could, two records in one dataset might be produced by different
implementations of the same contract, and the run would be impossible to reason
about afterwards.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping


class RegistryError(Exception):
    """Raised for registration and lookup failures.

    A plain exception rather than a framework error because ``shared`` sits
    beneath the domain and must not depend on the domain's exception hierarchy.
    Callers in higher layers translate it at their boundary.
    """


class Registry[T]:
    """An immutable-once-frozen mapping from name to registered value.

    Args:
        label: What the registry holds, used in error messages -- "strategy",
            "exporter". Naming it turns "not registered" into "no exporter named
            'parquet' is registered".
    """

    __slots__ = ("_entries", "_frozen", "_label")

    def __init__(self, label: str = "component") -> None:
        self._entries: dict[str, T] = {}
        self._frozen = False
        self._label = label

    def register(self, name: str, value: T, *, replace: bool = False) -> None:
        """Register ``value`` under ``name``.

        Args:
            name: Lookup key. Must be non-empty and, unless ``replace``, unused.
            value: The component to register.
            replace: Permit overwriting an existing entry. Off by default so that
                two components accidentally claiming one name fail loudly rather
                than one silently shadowing the other.

        Raises:
            RegistryError: If the registry is frozen, the name is empty, or the
                name is taken and ``replace`` is false.
        """
        if self._frozen:
            raise RegistryError(f"Cannot register {self._label} {name!r}: the registry is frozen")
        if not name or not name.strip():
            raise RegistryError(f"A {self._label} name must be a non-empty string")
        if name in self._entries and not replace:
            raise RegistryError(
                f"A {self._label} named {name!r} is already registered; "
                "pass replace=True to override it deliberately"
            )
        self._entries[name] = value

    def get(self, name: str) -> T:
        """Return the value registered under ``name``.

        Raises:
            RegistryError: If nothing is registered under that name. The message
                lists what is available, because a typo is the usual cause.
        """
        try:
            return self._entries[name]
        except KeyError:
            available = ", ".join(sorted(self._entries)) or "none"
            raise RegistryError(
                f"No {self._label} named {name!r} is registered (available: {available})"
            ) from None

    def get_or_none(self, name: str) -> T | None:
        """Return the value registered under ``name``, or ``None`` if absent."""
        return self._entries.get(name)

    def has(self, name: str) -> bool:
        """Whether anything is registered under ``name``."""
        return name in self._entries

    def names(self) -> tuple[str, ...]:
        """Every registered name, sorted for stable display."""
        return tuple(sorted(self._entries))

    def items(self) -> Mapping[str, T]:
        """A read-only view of the registered entries."""
        from types import MappingProxyType

        return MappingProxyType(dict(self._entries))

    def freeze(self) -> None:
        """Close the registry to further registration. Idempotent."""
        self._frozen = True

    @property
    def frozen(self) -> bool:
        """Whether the registry is closed to further registration."""
        return self._frozen

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[T]:
        return iter(self._entries.values())

    def __contains__(self, name: object) -> bool:
        return name in self._entries
