"""The checkpoint model and its integrity check.

A checkpoint is a durable "you are here" marker: enough of a workflow's state to
resume it safely after an interruption, without repeating completed work. It
records which stage completed, which dataset version was produced, and the
identities of the configuration, plugins, framework and schema in effect, so a
resume can verify the world has not changed underneath it before continuing.

Integrity is the load-bearing property. A resume that trusts a corrupt or
incomplete checkpoint is worse than no resume at all, so every checkpoint carries
a content hash of its own fields, and :meth:`verify_integrity` recomputes it. A
checkpoint that fails the check is refused, never resumed from.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from nexusai.shared.types import JsonValue

CHECKPOINT_VERSION = 1


@dataclass(frozen=True, slots=True, kw_only=True)
class Checkpoint:
    """A durable marker of workflow progress, resumable and self-verifying.

    Attributes:
        checkpoint_id: The checkpoint's identity.
        job_id: The job this checkpoint belongs to.
        workflow_version: The workflow version in effect.
        completed_stage: The last stage that completed successfully.
        next_stage: The stage to resume at, or ``None`` at the end.
        dataset_ref: The dataset version produced so far, if any.
        dataset_version: The dataset version number, if any.
        pagination_state: Opaque pagination progress, for mid-retrieval resume.
        configuration_ref: The effective configuration identity.
        plugin_versions: The versions of the plugins in use.
        framework_version: The framework version.
        schema_version: The persistence schema version.
        created_at: When the checkpoint was written.
        version: The checkpoint format version.
        integrity_hash: A hash of the checkpoint's fields, set on creation.
    """

    checkpoint_id: str
    job_id: str
    workflow_version: str
    completed_stage: str
    next_stage: str | None = None
    dataset_ref: str | None = None
    dataset_version: int | None = None
    pagination_state: Mapping[str, JsonValue] = field(default_factory=dict)
    configuration_ref: str | None = None
    plugin_versions: Mapping[str, str] = field(default_factory=dict)
    framework_version: str = ""
    schema_version: int = 0
    created_at: datetime | None = None
    version: int = CHECKPOINT_VERSION
    integrity_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "pagination_state", dict(self.pagination_state))
        object.__setattr__(self, "plugin_versions", dict(self.plugin_versions))
        if not self.integrity_hash:
            object.__setattr__(self, "integrity_hash", self._compute_hash())

    def _payload(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "job_id": self.job_id,
            "workflow_version": self.workflow_version,
            "completed_stage": self.completed_stage,
            "next_stage": self.next_stage,
            "dataset_ref": self.dataset_ref,
            "dataset_version": self.dataset_version,
            "pagination_state": dict(self.pagination_state),
            "configuration_ref": self.configuration_ref,
            "plugin_versions": dict(self.plugin_versions),
            "framework_version": self.framework_version,
            "schema_version": self.schema_version,
            "version": self.version,
        }

    def _compute_hash(self) -> str:
        payload = json.dumps(self._payload(), sort_keys=True, default=str)
        return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """Whether the checkpoint's recorded hash matches its current fields."""
        return bool(self.integrity_hash) and self.integrity_hash == self._compute_hash()

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation including the integrity hash."""
        payload = self._payload()
        payload["created_at"] = self.created_at.isoformat() if self.created_at else None
        payload["integrity_hash"] = self.integrity_hash
        return payload


class CheckpointIntegrityError(Exception):
    """A checkpoint failed its integrity or completeness check."""


def validate_checkpoint(
    checkpoint: Checkpoint, *, supported_version: int = CHECKPOINT_VERSION
) -> None:
    """Raise if ``checkpoint`` is unfit to resume from.

    Rejects a checkpoint whose hash does not verify, whose format version is
    newer than supported, or which is missing the references a resume needs.

    Raises:
        CheckpointIntegrityError: If the checkpoint is corrupt, incomplete or of
            an unsupported version.
    """
    if not checkpoint.verify_integrity():
        raise CheckpointIntegrityError("Checkpoint integrity hash does not match")
    if checkpoint.version > supported_version:
        raise CheckpointIntegrityError(
            f"Checkpoint version {checkpoint.version} is newer than supported "
            f"{supported_version}"
        )
    if not checkpoint.completed_stage:
        raise CheckpointIntegrityError("Checkpoint is missing its completed stage")
    if not checkpoint.job_id:
        raise CheckpointIntegrityError("Checkpoint is missing its job reference")
