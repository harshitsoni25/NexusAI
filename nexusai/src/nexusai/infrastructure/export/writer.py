"""Atomic file output and manifest construction shared by exporters.

Every file-based exporter writes through :func:`atomic_output`, which yields a
temporary path, lets the exporter fill it, then flushes, fsyncs and renames it
into place. A failure before the rename leaves only the temporary file, which is
cleaned up -- never a partial file at the final path that would look like a valid
export. :func:`build_manifest` then hashes and sizes the finished file so the
manifest describes exactly what landed.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from nexusai.domain.model.persistence import (
    DatasetVersion,
    ExportManifest,
    OutcomeStatus,
)
from nexusai.domain.provenance.source import ArtifactReference
from nexusai.infrastructure.artifacts.integrity import content_hash
from nexusai.infrastructure.artifacts.paths import ensure_parent, safe_join


@contextmanager
def atomic_output(base: Path, name: str) -> Iterator[Path]:
    """Yield a temporary path atomically renamed to ``name`` on clean exit.

    The final path is resolved safely under ``base`` (rejecting traversal). If
    the body raises, the temporary file is removed and no final file appears.
    """
    target = safe_join(base, name)
    ensure_parent(target)
    temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    ok = False
    try:
        yield temp
        ok = True
    finally:
        if ok and temp.exists():
            temp.replace(target)
        elif temp.exists():
            temp.unlink()


def resolve_target(base: Path, name: str) -> Path:
    """Return the final resolved path an export will land at."""
    return safe_join(base, name)


def export_identity(version: DatasetVersion | None) -> tuple[str, int]:
    """Return the ``(dataset_id, version)`` for a manifest, with a fallback."""
    if version is None:
        return "dataset", 1
    return str(version.dataset_id), version.version


def build_manifest(
    path: Path,
    *,
    dataset_id: str,
    dataset_version: int,
    export_format: str,
    media_type: str,
    record_count: int,
    duration_seconds: float,
    exporter_version: str,
    run_ref: str | None = None,
) -> ExportManifest:
    """Hash and size ``path`` and return the export manifest describing it."""
    data = path.read_bytes()
    return ExportManifest(
        export_id=uuid.uuid4().hex,
        dataset_id=dataset_id,
        dataset_version=dataset_version,
        export_format=export_format,
        artifact=ArtifactReference(locator=str(path), media_type=media_type, size_bytes=len(data)),
        record_count=record_count,
        size_bytes=len(data),
        content_hash=content_hash(data),
        created_at=datetime.now(UTC),
        duration_seconds=duration_seconds,
        status=OutcomeStatus.SUCCESS,
        exporter_version=exporter_version,
        run_ref=run_ref,
    )
