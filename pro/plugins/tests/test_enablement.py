"""The persisted enable/disable overlay."""

from __future__ import annotations

from nexusai_pro_plugins import EnablementStore


def test_default_enabled_and_toggle(tmp_path):
    store = EnablementStore(tmp_path / "en.json")
    assert store.is_enabled("p1") is True  # enabled unless explicitly disabled
    store.set_enabled("p1", False)
    assert store.is_enabled("p1") is False
    assert store.disabled_ids() == {"p1"}
    store.set_enabled("p1", True)
    assert store.is_enabled("p1") is True


def test_persists_across_instances(tmp_path):
    path = tmp_path / "en.json"
    EnablementStore(path).set_enabled("p2", False)
    assert EnablementStore(path).is_enabled("p2") is False


def test_forget_and_filter(tmp_path):
    store = EnablementStore(tmp_path / "en.json")
    store.set_enabled("a", False)
    store.set_enabled("b", False)
    assert set(store.filter_enabled(["a", "b", "c"])) == {"c"}
    store.forget("a")
    assert store.is_enabled("a") is True
