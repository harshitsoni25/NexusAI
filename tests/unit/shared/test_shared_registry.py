"""Tests for the typed, name-keyed registry."""

from __future__ import annotations

import pytest

from nexusai.shared.registry import Registry, RegistryError


def test_register_and_get() -> None:
    registry: Registry[str] = Registry("widget")
    registry.register("a", "alpha")
    assert registry.get("a") == "alpha"


def test_get_unknown_raises_with_available_listed() -> None:
    registry: Registry[str] = Registry("widget")
    registry.register("a", "alpha")
    with pytest.raises(RegistryError, match=r"No widget named 'z'.*available: a"):
        registry.get("z")


def test_get_unknown_reports_none_when_empty() -> None:
    registry: Registry[str] = Registry()
    with pytest.raises(RegistryError, match="available: none"):
        registry.get("missing")


def test_get_or_none_returns_none_for_missing() -> None:
    registry: Registry[str] = Registry()
    assert registry.get_or_none("missing") is None
    registry.register("a", "alpha")
    assert registry.get_or_none("a") == "alpha"


def test_duplicate_registration_rejected_by_default() -> None:
    registry: Registry[int] = Registry("number")
    registry.register("one", 1)
    with pytest.raises(RegistryError, match="already registered"):
        registry.register("one", 2)


def test_duplicate_registration_allowed_with_replace() -> None:
    registry: Registry[int] = Registry()
    registry.register("one", 1)
    registry.register("one", 2, replace=True)
    assert registry.get("one") == 2


@pytest.mark.parametrize("name", ["", "   "])
def test_empty_name_rejected(name: str) -> None:
    registry: Registry[int] = Registry()
    with pytest.raises(RegistryError, match="non-empty"):
        registry.register(name, 1)


def test_freeze_blocks_further_registration() -> None:
    registry: Registry[int] = Registry("thing")
    registry.register("a", 1)
    registry.freeze()
    assert registry.frozen is True
    with pytest.raises(RegistryError, match="frozen"):
        registry.register("b", 2)


def test_freeze_is_idempotent() -> None:
    registry: Registry[int] = Registry()
    registry.freeze()
    registry.freeze()
    assert registry.frozen is True


def test_has_and_contains() -> None:
    registry: Registry[int] = Registry()
    registry.register("a", 1)
    assert registry.has("a")
    assert "a" in registry
    assert "b" not in registry


def test_names_are_sorted() -> None:
    registry: Registry[int] = Registry()
    registry.register("c", 3)
    registry.register("a", 1)
    registry.register("b", 2)
    assert registry.names() == ("a", "b", "c")


def test_items_is_a_read_only_view() -> None:
    registry: Registry[int] = Registry()
    registry.register("a", 1)
    items = registry.items()
    assert dict(items) == {"a": 1}
    with pytest.raises(TypeError):
        items["b"] = 2  # type: ignore[index]


def test_len_and_iteration_over_values() -> None:
    registry: Registry[int] = Registry()
    registry.register("a", 1)
    registry.register("b", 2)
    assert len(registry) == 2
    assert sorted(registry) == [1, 2]
