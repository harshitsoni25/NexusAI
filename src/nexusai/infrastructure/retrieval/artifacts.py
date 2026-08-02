"""Writing retrieval artefacts -- screenshots, downloads, HTML snapshots.

A provider captures bytes; where they are kept is not its concern. The
:class:`ArtifactWriter` protocol is the seam: a provider hands over bytes and a
name and receives an :class:`ArtifactReference` to record on the document's
provenance. A filesystem writer serves production; an in-memory writer keeps
tests hermetic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from nexusai.domain.provenance.source import ArtifactReference


@runtime_checkable
class ArtifactWriter(Protocol):
    """Stores artefact bytes and returns a reference to them."""

    def write(self, name: str, data: bytes, media_type: str) -> ArtifactReference:
        """Persist ``data`` under ``name`` and return a reference to it."""
        ...


class InMemoryArtifactWriter:
    """An artefact writer that keeps bytes in memory.

    For tests and for callers that only need the reference and size without a
    durable store. The stored bytes are readable back through :attr:`items`.
    """

    def __init__(self) -> None:
        self.items: dict[str, bytes] = {}

    def write(self, name: str, data: bytes, media_type: str) -> ArtifactReference:
        """Store ``data`` under ``name`` in memory."""
        self.items[name] = data
        return ArtifactReference(
            locator=f"memory://{name}",
            media_type=media_type,
            description=name,
            size_bytes=len(data),
        )


class FilesystemArtifactWriter:
    """An artefact writer that stores bytes under a base directory."""

    def __init__(self, base_dir: Path) -> None:
        self._base = base_dir

    def write(self, name: str, data: bytes, media_type: str) -> ArtifactReference:
        """Write ``data`` to ``name`` beneath the base directory."""
        target = self._base / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return ArtifactReference(
            locator=str(target),
            media_type=media_type,
            description=name,
            size_bytes=len(data),
        )
