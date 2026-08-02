"""Artifact storage: write/read, hashing, integrity, and path safety."""

from __future__ import annotations

from pathlib import Path

import pytest

from nexusai.domain.errors.exceptions import StorageError
from nexusai.domain.model.persistence import ArtifactType
from nexusai.infrastructure.artifacts import (
    FilesystemArtifactStore,
    InMemoryArtifactStore,
    content_hash,
    safe_join,
    verify_hash,
)


class TestHashing:
    def test_hash_is_stable_and_algorithm_tagged(self) -> None:
        digest = content_hash(b"payload")
        assert digest.startswith("sha256:")
        assert content_hash(b"payload") == digest

    def test_verify_hash_detects_mismatch(self) -> None:
        assert verify_hash(b"a", content_hash(b"a"))
        assert not verify_hash(b"b", content_hash(b"a"))


class TestFilesystemStore:
    def test_write_and_read_round_trips(self, tmp_path: Path) -> None:
        store = FilesystemArtifactStore(tmp_path)
        meta = store.put(
            "s/page.html", b"<html>", "text/html", artifact_type=ArtifactType.HTML_SNAPSHOT
        )
        assert store.get(meta.artifact_id) == b"<html>"
        assert meta.size_bytes == 6

    def test_integrity_holds_for_untouched_artifact(self, tmp_path: Path) -> None:
        store = FilesystemArtifactStore(tmp_path)
        meta = store.put(
            "a.bin", b"data", "application/octet-stream", artifact_type=ArtifactType.OTHER
        )
        assert store.verify(meta.artifact_id)

    def test_integrity_fails_after_modification(self, tmp_path: Path) -> None:
        store = FilesystemArtifactStore(tmp_path)
        meta = store.put(
            "a.bin", b"data", "application/octet-stream", artifact_type=ArtifactType.OTHER
        )
        Path(meta.locator).write_bytes(b"tampered")
        assert not store.verify(meta.artifact_id)

    def test_missing_artifact_raises(self, tmp_path: Path) -> None:
        store = FilesystemArtifactStore(tmp_path)
        with pytest.raises(StorageError):
            store.get("nope")


class TestInMemoryStore:
    def test_round_trip_and_integrity(self) -> None:
        store = InMemoryArtifactStore()
        meta = store.put("x", b"bytes", "text/plain", artifact_type=ArtifactType.OTHER)
        assert store.get(meta.artifact_id) == b"bytes"
        assert store.verify(meta.artifact_id)


class TestPathSafety:
    def test_traversal_is_blocked(self, tmp_path: Path) -> None:
        with pytest.raises(StorageError):
            safe_join(tmp_path, "../../etc/passwd")

    def test_absolute_paths_are_blocked(self, tmp_path: Path) -> None:
        with pytest.raises(StorageError):
            safe_join(tmp_path, "/etc/passwd")

    def test_empty_names_are_blocked(self, tmp_path: Path) -> None:
        with pytest.raises(StorageError):
            safe_join(tmp_path, "  ")

    def test_symlink_escape_is_blocked(self, tmp_path: Path) -> None:
        outside = tmp_path / "outside"
        outside.mkdir()
        base = tmp_path / "base"
        base.mkdir()
        try:
            (base / "link").symlink_to(outside)
        except OSError as exc:
            # Windows refuses symlink creation without the privilege or Developer
            # Mode (WinError 1314). Skip only when the fixture itself cannot be
            # created; wherever symlinks are supported, the security assertion runs.
            pytest.skip(f"symlink creation not permitted in this environment: {exc}")
        with pytest.raises(StorageError):
            safe_join(base, "link/secret.txt")

    def test_nested_relative_paths_are_allowed(self, tmp_path: Path) -> None:
        resolved = safe_join(tmp_path, "a/b/c.txt")
        assert str(resolved).startswith(str(tmp_path.resolve()))
