"""Tests for JSON-safe serialisation of framework values."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import Enum

from nexusai.shared.serialization import SelfSerialising, to_primitive


class Colour(Enum):
    RED = "red"
    GREEN = 2


@dataclass(frozen=True)
class Point:
    x: int
    y: int


class Custom:
    """A value that renders itself via to_dict."""

    def to_dict(self) -> dict[str, object]:
        return {"kind": "custom", "when": datetime(2026, 1, 1, tzinfo=UTC)}


def test_scalars_pass_through() -> None:
    assert to_primitive("s") == "s"
    assert to_primitive(3) == 3
    assert to_primitive(1.5) == 1.5
    assert to_primitive(True) is True
    assert to_primitive(None) is None


def test_enum_uses_its_value() -> None:
    assert to_primitive(Colour.RED) == "red"
    assert to_primitive(Colour.GREEN) == 2


def test_datetime_and_date_are_isoformatted() -> None:
    assert to_primitive(datetime(2026, 1, 2, 3, 4, tzinfo=UTC)) == "2026-01-02T03:04:00+00:00"
    assert to_primitive(date(2026, 1, 2)) == "2026-01-02"


def test_dataclass_becomes_a_mapping() -> None:
    assert to_primitive(Point(1, 2)) == {"x": 1, "y": 2}


def test_self_serialising_takes_precedence_and_recurses() -> None:
    assert to_primitive(Custom()) == {"kind": "custom", "when": "2026-01-01T00:00:00+00:00"}


def test_mapping_keys_are_stringified() -> None:
    assert to_primitive({1: "a", "b": 2}) == {"1": "a", "b": 2}


def test_sequences_are_converted_elementwise() -> None:
    assert to_primitive([Colour.RED, Point(0, 0)]) == ["red", {"x": 0, "y": 0}]
    assert to_primitive((1, 2)) == [1, 2]


def test_sets_are_sorted_for_determinism() -> None:
    assert to_primitive({3, 1, 2}) == [1, 2, 3]


def test_unknown_object_falls_back_to_str() -> None:
    class Opaque:
        def __str__(self) -> str:
            return "opaque"

    assert to_primitive(Opaque()) == "opaque"


def test_self_serialising_protocol_recognises_to_dict() -> None:
    assert isinstance(Custom(), SelfSerialising)
    assert not isinstance(object(), SelfSerialising)
