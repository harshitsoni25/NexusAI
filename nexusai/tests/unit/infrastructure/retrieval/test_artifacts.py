"""Tests for the artefact writers."""

from __future__ import annotations

from pathlib import Path

from nexusai.infrastructure.retrieval.artifacts import (
    FilesystemArtifactWriter,
    InMemoryArtifactWriter,
)


def test_in_memory_writer_stores_and_references() -> None:
    writer = InMemoryArtifactWriter()
    ref = writer.write("shot.png", b"data", "image/png")
    assert writer.items["shot.png"] == b"data"
    assert ref.locator == "memory://shot.png"
    assert ref.media_type == "image/png"
    assert ref.size_bytes == 4


def test_filesystem_writer_persists_bytes(tmp_path: Path) -> None:
    writer = FilesystemArtifactWriter(tmp_path)
    ref = writer.write("nested/shot.png", b"bytes", "image/png")
    written = tmp_path / "nested" / "shot.png"
    assert written.read_bytes() == b"bytes"
    assert ref.locator == str(written)
    assert ref.size_bytes == 5
