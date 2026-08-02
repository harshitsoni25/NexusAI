"""Type aliases and sentinels used across the framework."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import Enum

type JsonScalar = str | int | float | bool | None
"""Any JSON value that is not a container."""

type JsonValue = JsonScalar | Sequence[JsonValue] | Mapping[str, JsonValue]
"""Any value expressible in JSON. Recursive, as JSON itself is."""

type JsonMapping = Mapping[str, JsonValue]
"""A JSON object."""

type MutableJsonMapping = dict[str, JsonValue]
"""A mutable JSON object, used while building configuration layers."""


class Unset(Enum):
    """The type of the :data:`UNSET` sentinel.

    Implemented as a single-member enum so that static type checkers can narrow
    ``value is UNSET`` correctly, which a bare ``object()`` sentinel does not
    allow.
    """

    TOKEN = "UNSET"

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET: Unset = Unset.TOKEN
"""Sentinel distinguishing "no value supplied" from an explicit ``None``.

Configuration layering needs this distinction: a layer that omits a key must
not override a lower-precedence layer, while a layer that explicitly sets the
key to ``None`` must.
"""
