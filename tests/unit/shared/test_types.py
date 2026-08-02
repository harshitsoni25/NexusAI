"""Sentinels."""

from __future__ import annotations

from nexusai.shared.types import UNSET, Unset


def test_unset_is_falsey_and_distinguishable_from_none() -> None:
    # Configuration layering depends on this: a layer that omits a key must not
    # override a lower layer, while a layer that explicitly sets None must.
    assert not UNSET
    assert UNSET is not None
    assert isinstance(UNSET, Unset)


def test_unset_has_a_readable_repr() -> None:
    assert repr(UNSET) == "UNSET"
