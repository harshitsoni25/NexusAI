"""Tests for the small mapping helpers."""

from __future__ import annotations

from nexusai.shared.mapping import compact, map_values, omit, rename, select


def test_select_keeps_only_present_requested_keys() -> None:
    assert select({"a": 1, "b": 2, "c": 3}, ["a", "c", "z"]) == {"a": 1, "c": 3}


def test_omit_removes_named_keys() -> None:
    assert omit({"a": 1, "b": 2}, ["b"]) == {"a": 1}


def test_rename_maps_keys_and_passes_others_through() -> None:
    assert rename({"a": 1, "b": 2}, {"a": "alpha"}) == {"alpha": 1, "b": 2}


def test_map_values_applies_function() -> None:
    assert map_values({"a": 1, "b": 2}, lambda v: v * 10) == {"a": 10, "b": 20}


def test_compact_drops_none_values() -> None:
    assert compact({"a": 1, "b": None, "c": 0}) == {"a": 1, "c": 0}


def test_helpers_return_new_mappings() -> None:
    source = {"a": 1}
    assert select(source, ["a"]) is not source
    assert omit(source, []) is not source
