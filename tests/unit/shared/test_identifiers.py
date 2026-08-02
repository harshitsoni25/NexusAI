"""Identifier value objects."""

from __future__ import annotations

import pytest

from nexusai.shared.identifiers import CorrelationId, JobId, RunId


def test_identifier_renders_as_its_value() -> None:
    assert str(CorrelationId("abc-123")) == "abc-123"


def test_identifiers_are_frozen() -> None:
    identifier = RunId("run-1")
    with pytest.raises(AttributeError):
        identifier.value = "run-2"  # type: ignore[misc]


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_identifiers_are_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        JobId(value)


def test_of_strips_surrounding_whitespace() -> None:
    assert JobId.of("  job-7 ").value == "job-7"


def test_distinct_types_are_not_equal_even_with_the_same_value() -> None:
    # The whole point of wrapping: a job id must never satisfy a run id parameter.
    # MyPy proves the same property statically, which is why the comparison
    # needs an ignore: it reports the types as non-overlapping.
    assert JobId("x") != RunId("x")  # type: ignore[comparison-overlap]


def test_identifiers_are_hashable() -> None:
    assert len({CorrelationId("a"), CorrelationId("a"), CorrelationId("b")}) == 2
