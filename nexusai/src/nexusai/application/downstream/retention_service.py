"""Application service for retention and cleanup.

Applies the pure :class:`RetentionPolicy` to a collection of stored artefacts and
produces a plan of what may be deleted -- separating the decision (policy) from
the act (this service). Nothing is deleted unless the caller runs the plan, and
audit-class artefacts never appear in a plan, so the destructive path can never
touch history. The plan is returned so a caller can review it before acting.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from nexusai.domain.model.persistence import ArtifactMetadata
from nexusai.domain.policy.retention import RetentionPolicy


@dataclass(frozen=True, slots=True)
class RetentionPlan:
    """A reviewable plan of which artefacts may be deleted and which are kept."""

    deletable: tuple[ArtifactMetadata, ...]
    retained: tuple[ArtifactMetadata, ...]


class RetentionService:
    """Plans and executes retention-driven cleanup over stored artefacts."""

    def __init__(self, policy: RetentionPolicy) -> None:
        self._policy = policy

    def plan(
        self,
        artifacts: Sequence[ArtifactMetadata],
        *,
        now: datetime | None = None,
    ) -> RetentionPlan:
        """Partition ``artifacts`` into deletable and retained by policy."""
        moment = now or datetime.now(UTC)
        deletable: list[ArtifactMetadata] = []
        retained: list[ArtifactMetadata] = []
        for artifact in artifacts:
            age = (moment - artifact.created_at).total_seconds()
            if self._policy.may_delete(artifact.artifact_type, age):
                deletable.append(artifact)
            else:
                retained.append(artifact)
        return RetentionPlan(deletable=tuple(deletable), retained=tuple(retained))

    def execute(self, plan: RetentionPlan, delete: Callable[[ArtifactMetadata], None]) -> int:
        """Delete every artefact in ``plan.deletable`` via ``delete``.

        Only the deletable set is passed to ``delete``; retained (including all
        audit) artefacts are never touched. Returns how many were deleted.
        """
        for artifact in plan.deletable:
            delete(artifact)
        return len(plan.deletable)
