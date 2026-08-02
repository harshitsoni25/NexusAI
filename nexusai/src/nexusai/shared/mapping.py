"""Small, pure helpers for reshaping mappings.

The framework moves data across boundaries -- settings into a snapshot, a model
into a report row, one DTO into another. These helpers cover the recurring
mechanics of that reshaping without pulling in a mapping library, which would be
premature for needs this modest.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping


def select[K, V](source: Mapping[K, V], keys: Iterable[K]) -> dict[K, V]:
    """Return a new mapping containing only ``keys`` that are present."""
    wanted = set(keys)
    return {key: value for key, value in source.items() if key in wanted}


def omit[K, V](source: Mapping[K, V], keys: Iterable[K]) -> dict[K, V]:
    """Return a new mapping with ``keys`` removed."""
    unwanted = set(keys)
    return {key: value for key, value in source.items() if key not in unwanted}


def rename[V](source: Mapping[str, V], mapping: Mapping[str, str]) -> dict[str, V]:
    """Return a new mapping with keys renamed per ``mapping``.

    Keys absent from ``mapping`` are carried through unchanged.
    """
    return {mapping.get(key, key): value for key, value in source.items()}


def map_values[K, V, W](source: Mapping[K, V], func: Callable[[V], W]) -> dict[K, W]:
    """Return a new mapping with ``func`` applied to every value."""
    return {key: func(value) for key, value in source.items()}


def compact[K, V](source: Mapping[K, V | None]) -> dict[K, V]:
    """Return a new mapping with ``None`` values dropped.

    Useful when assembling an export row or a report payload where an absent
    value should be omitted rather than rendered as null.
    """
    return {key: value for key, value in source.items() if value is not None}
