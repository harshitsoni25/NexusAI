"""Atomic report output and report-manifest construction.

Report renderers write through the same atomic-output discipline as exporters --
temporary file, fsync, rename -- so a failed render never leaves a partial report
that looks complete. :func:`build_report_manifest` hashes and sizes the finished
file, giving every report an auditable manifest tied to its dataset version.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from nexusai.domain.model.persistence import OutcomeStatus, ReportManifest
from nexusai.domain.provenance.source import ArtifactReference
from nexusai.infrastructure.artifacts.integrity import content_hash
from nexusai.infrastructure.export.writer import atomic_output, resolve_target

__all__ = ["atomic_output", "build_report_manifest", "resolve_target"]


def build_report_manifest(
    path: Path,
    *,
    dataset_id: str,
    dataset_version: int,
    report_format: str,
    media_type: str,
    generator_version: str,
    run_ref: str | None = None,
) -> ReportManifest:
    """Hash and size ``path`` and return the report manifest describing it."""
    data = path.read_bytes()
    return ReportManifest(
        report_id=uuid.uuid4().hex,
        dataset_id=dataset_id,
        dataset_version=dataset_version,
        report_format=report_format,
        artifact=ArtifactReference(locator=str(path), media_type=media_type, size_bytes=len(data)),
        size_bytes=len(data),
        content_hash=content_hash(data),
        created_at=datetime.now(UTC),
        status=OutcomeStatus.SUCCESS,
        generator_version=generator_version,
        run_ref=run_ref,
    )
