"""Reusable metadata value objects.

``Metadata`` is an immutable, typed bag of descriptive key-value pairs, used
wherever a framework object needs to carry auxiliary description that the core
should not enumerate in advance -- tags on a component, attributes on an event.
Typed accessors are provided so that reading a value does not scatter ``isinstance``
checks across the codebase.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from nexusai.shared.types import JsonMapping, JsonValue


@dataclass(frozen=True, slots=True)
class Metadata:
    """An immutable, typed collection of descriptive key-value pairs.

    Immutability is the point: metadata is attached at creation and read
    thereafter, never mutated in place, so it can be shared freely without a
    reader having to worry that a writer elsewhere will change it.
    """

    values: JsonMapping = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Copy into a plain dict so that a mutable mapping passed in by a caller
        # cannot be changed underneath us after construction.
        object.__setattr__(self, "values", dict(self.values))

    def get(self, key: str, default: JsonValue = None) -> JsonValue:
        """Return the value for ``key``, or ``default`` if absent."""
        return self.values.get(key, default)

    def get_str(self, key: str, default: str = "") -> str:
        """Return ``key`` as a string, or ``default`` if absent or not a string."""
        value = self.values.get(key)
        return value if isinstance(value, str) else default

    def get_int(self, key: str, default: int = 0) -> int:
        """Return ``key`` as an int, or ``default`` if absent or not an int.

        Booleans are rejected even though they are technically integers, because
        a metadata value of ``True`` read as ``1`` is almost always a mistake.
        """
        value = self.values.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) else default

    def get_bool(self, key: str, *, default: bool = False) -> bool:
        """Return ``key`` as a bool, or ``default`` if absent or not a bool."""
        value = self.values.get(key)
        return value if isinstance(value, bool) else default

    def with_values(self, **updates: JsonValue) -> Metadata:
        """Return a new ``Metadata`` with ``updates`` applied over this one."""
        return Metadata({**self.values, **updates})

    def merge(self, other: Metadata) -> Metadata:
        """Return a new ``Metadata`` with ``other`` layered over this one."""
        return Metadata({**self.values, **other.values})

    def __contains__(self, key: object) -> bool:
        return key in self.values

    def __iter__(self) -> Iterator[str]:
        return iter(self.values)

    def __len__(self) -> int:
        return len(self.values)

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return dict(self.values)

    @classmethod
    def empty(cls) -> Metadata:
        """Return an empty metadata instance."""
        return cls({})


@dataclass(frozen=True, slots=True, kw_only=True)
class EventMetadata:
    """Descriptive context attached to an event as it is published.

    Distinct from the event's own fields: the event says *what happened*, this
    says *about the act of publishing it* -- which component emitted it, in which
    stage, with what tags. Subscribers use it to filter and route without the
    event type having to grow a field for every possible consumer.

    Attributes:
        source: Dotted name of the component that published the event.
        stage: The processing stage in effect when it was published, if any.
        tags: Free-form labels for routing and filtering.
    """

    source: str
    stage: str | None = None
    tags: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tags", dict(self.tags))

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {"source": self.source, "stage": self.stage, "tags": dict(self.tags)}
