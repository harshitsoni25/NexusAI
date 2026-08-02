"""Tests for Metadata and EventMetadata."""

from __future__ import annotations

from nexusai.domain.model.metadata import EventMetadata, Metadata


def test_typed_getters_return_matching_types() -> None:
    meta = Metadata({"s": "text", "n": 5, "flag": True})
    assert meta.get_str("s") == "text"
    assert meta.get_int("n") == 5
    assert meta.get_bool("flag") is True


def test_typed_getters_fall_back_on_type_mismatch() -> None:
    meta = Metadata({"s": 1, "n": "x", "flag": "y"})
    assert meta.get_str("s") == ""
    assert meta.get_int("n") == 0
    assert meta.get_bool("flag") is False


def test_get_int_rejects_bool() -> None:
    # True is an int in Python, but semantically it is not an integer value.
    assert Metadata({"n": True}).get_int("n", default=-1) == -1


def test_defaults_used_for_missing_keys() -> None:
    meta = Metadata.empty()
    assert meta.get("missing", "d") == "d"
    assert meta.get_str("missing", "d") == "d"
    assert meta.get_int("missing", 9) == 9
    assert meta.get_bool("missing", default=True) is True


def test_with_values_and_merge_are_immutable() -> None:
    base = Metadata({"a": 1})
    updated = base.with_values(b=2)
    assert dict(base.values) == {"a": 1}
    assert updated.get("b") == 2
    merged = base.merge(Metadata({"a": 9, "c": 3}))
    assert merged.get("a") == 9
    assert merged.get("c") == 3


def test_source_mapping_is_copied_defensively() -> None:
    source = {"a": 1}
    meta = Metadata(source)
    source["a"] = 99
    assert meta.get("a") == 1


def test_container_dunders() -> None:
    meta = Metadata({"a": 1, "b": 2})
    assert "a" in meta
    assert len(meta) == 2
    assert sorted(meta) == ["a", "b"]


def test_event_metadata_serialises_and_copies_tags() -> None:
    tags = {"env": "test"}
    em = EventMetadata(source="comp", stage="parse", tags=tags)
    tags["env"] = "mutated"
    assert em.to_dict() == {"source": "comp", "stage": "parse", "tags": {"env": "test"}}


def test_metadata_to_dict_returns_plain_mapping() -> None:
    assert Metadata({"a": 1, "b": "x"}).to_dict() == {"a": 1, "b": "x"}
