"""The Result type."""

from __future__ import annotations

import pytest

from nexusai.shared.result import Err, Ok, is_err, is_ok


def test_ok_unwraps_to_its_value() -> None:
    assert Ok(42).unwrap() == 42


def test_ok_ignores_the_default() -> None:
    assert Ok(42).unwrap_or(0) == 42


def test_err_unwrap_raises() -> None:
    with pytest.raises(ValueError, match="Err"):
        Err("broken").unwrap()


def test_err_falls_back_to_the_default() -> None:
    assert Err("broken").unwrap_or(7) == 7


def test_map_applies_only_on_success() -> None:
    assert Ok(2).map(lambda value: value * 3) == Ok(6)
    assert Err("boom").map(lambda value: value * 3) == Err("boom")


def test_guards_narrow_the_union() -> None:
    success: Ok[int] | Err[str] = Ok(1)
    failure: Ok[int] | Err[str] = Err("no")
    assert is_ok(success) and not is_err(success)
    assert is_err(failure) and not is_ok(failure)
