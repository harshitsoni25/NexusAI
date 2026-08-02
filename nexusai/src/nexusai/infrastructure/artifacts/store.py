"""Filesystem artefact store with content-hash integrity.

Implements the domain's :class:`ArtifactStore` behind a local directory, while
exposing only backend-independent metadata so a future object store can replace
it without touching callers. Bytes are written atomically -- to a temporary file
that is flushed, fsynced and renamed into place -- so a crash mid-write never
leaves a half-written artefact that would fail its own integrity check.

Every stored artefact is hashed on the way in; :meth:`verify` re-reads and
re-hashes to confirm the bytes on disk still match, which is how modification and
corruption are detected after the fact. An in-memory variant backs tests and
small runs without touching the filesystem.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from nexusai.domain.errors.exceptions import StorageError
from nexusai.domain.model.persistence import ArtifactMetadata, ArtifactType
from nexusai.infrastructure.artifacts.integrity import content_hash, verify_hash
from nexusai.infrastructure.artifacts.paths import ensure_parent, safe_join


class FilesystemArtifactStore:
    """Stores artefact bytes under a base directory, with integrity metadata."""

    def __init__(self, base_dir: Path) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)
        self._metadata: dict[str, ArtifactMetadata] = {}

    def put(
        self,
        name: str,
        data: bytes,
        media_type: str,
        *,
        artifact_type: ArtifactType,
        dataset_id: str | None = None,
        dataset_version: int | None = None,
        run_ref: str | None = None,
    ) -> ArtifactMetadata:
        """Store ``data`` atomically and return its metadata."""
        target = safe_join(self._base, name)
        ensure_parent(target)
        _atomic_write(target, data)
        artifact_id = uuid.uuid4().hex
        metadata = ArtifactMetadata(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            locator=str(target),
            media_type=media_type,
            size_bytes=len(data),
            content_hash=content_hash(data),
            created_at=datetime.now(UTC),
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            run_ref=run_ref,
        )
        self._metadata[artifact_id] = metadata
        return metadata

    def get(self, artifact_id: str) -> bytes:
        """Return the stored bytes of an artefact."""
        metadata = self._require(artifact_id)
        return Path(metadata.locator).read_bytes()

    def metadata(self, artifact_id: str) -> ArtifactMetadata | None:
        """Return an artefact's metadata, or ``None`` if absent."""
        return self._metadata.get(artifact_id)

    def verify(self, artifact_id: str) -> bool:
        """Re-read the artefact and confirm its bytes still match the hash."""
        metadata = self._require(artifact_id)
        path = Path(metadata.locator)
        if not path.exists():
            return False
        return verify_hash(path.read_bytes(), metadata.content_hash)

    def _require(self, artifact_id: str) -> ArtifactMetadata:
        metadata = self._metadata.get(artifact_id)
        if metadata is None:
            raise StorageError("No such artefact", artifact_id=artifact_id)
        return metadata


class InMemoryArtifactStore:
    """An artefact store backed by a dictionary, for tests and small runs."""

    def __init__(self) -> None:
        self._bytes: dict[str, bytes] = {}
        self._metadata: dict[str, ArtifactMetadata] = {}

    def put(
        self,
        name: str,
        data: bytes,
        media_type: str,
        *,
        artifact_type: ArtifactType,
        dataset_id: str | None = None,
        dataset_version: int | None = None,
        run_ref: str | None = None,
    ) -> ArtifactMetadata:
        """Store ``data`` in memory and return its metadata."""
        artifact_id = uuid.uuid4().hex
        metadata = ArtifactMetadata(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            locator=f"memory://{name}",
            media_type=media_type,
            size_bytes=len(data),
            content_hash=content_hash(data),
            created_at=datetime.now(UTC),
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            run_ref=run_ref,
        )
        self._bytes[artifact_id] = data
        self._metadata[artifact_id] = metadata
        return metadata

    def get(self, artifact_id: str) -> bytes:
        """Return the stored bytes of an artefact."""
        if artifact_id not in self._bytes:
            raise StorageError("No such artefact", artifact_id=artifact_id)
        return self._bytes[artifact_id]

    def metadata(self, artifact_id: str) -> ArtifactMetadata | None:
        """Return an artefact's metadata, or ``None`` if absent."""
        return self._metadata.get(artifact_id)

    def verify(self, artifact_id: str) -> bool:
        """Confirm the in-memory bytes still match the recorded hash."""
        if artifact_id not in self._bytes:
            return False
        return verify_hash(self._bytes[artifact_id], self._metadata[artifact_id].content_hash)


def _atomic_write(target: Path, data: bytes) -> None:
    temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        temp.replace(target)
    finally:
        if temp.exists():
            temp.unlink()
