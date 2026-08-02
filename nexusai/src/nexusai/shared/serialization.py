"""Conversion of framework values into JSON-safe primitives.

Logs, reports, exports and event payloads all need to render domain values as
plain data. Centralising the rules here means a datetime, an enum or a frozen
dataclass serialises the same way everywhere, rather than each call site
inventing its own and disagreeing at the edges.

The function is total over the types the framework actually uses and refuses
silently lossy conversions: an unknown object is rendered through a declared
hook or via ``str``, never dropped.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from nexusai.shared.types import JsonValue


@runtime_checkable
class SelfSerialising(Protocol):
    """A value that knows how to render itself as a JSON-safe mapping."""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""
        ...


def to_primitive(value: Any) -> JsonValue:
    """Render ``value`` as JSON-safe primitives.

    The order of checks matters. A value that declares ``to_dict`` is trusted to
    describe itself before structural rules apply, so a model can present a
    curated shape rather than its raw fields. Enums contribute their value,
    datetimes their ISO-8601 string, dataclasses their fields, mappings and
    sequences their recursively converted contents.

    Args:
        value: Any framework value.

    Returns:
        A structure of dicts, lists, strings, numbers, booleans and ``None``.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, SelfSerialising):
        return {key: to_primitive(item) for key, item in value.to_dict().items()}
    if isinstance(value, Enum):
        return to_primitive(value.value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return {key: to_primitive(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): to_primitive(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset)):
        return [to_primitive(item) for item in sorted(value, key=repr)]
    if isinstance(value, Sequence):
        return [to_primitive(item) for item in value]
    return str(value)
