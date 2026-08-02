"""Pure retention policy.

Whether an artefact may be deleted is a judgement, so it lives in policy where it
can be read and tested without a filesystem. The policy classifies every artefact
into one of three retention classes and answers one question -- may this be
deleted, given its age? -- without performing any deletion itself. Execution is
the application layer's job; deciding is policy's.

The load-bearing rule: audit-class artefacts are never deletable, whatever their
age. A retention policy that could quietly remove audit history would defeat the
purpose of keeping it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from nexusai.domain.model.persistence import ArtifactType


class RetentionClass(Enum):
    """How an artefact is treated by retention.

    Attributes:
        TEMPORARY: Working data safe to delete once past its age limit.
        REPRODUCIBILITY: Kept to reproduce an output; deletable when old.
        AUDIT: History that must never be deleted by policy.
    """

    TEMPORARY = "temporary"
    REPRODUCIBILITY = "reproducibility"
    AUDIT = "audit"


_CLASS_BY_TYPE = {
    ArtifactType.HTML_SNAPSHOT: RetentionClass.REPRODUCIBILITY,
    ArtifactType.DOM_SNAPSHOT: RetentionClass.REPRODUCIBILITY,
    ArtifactType.SCREENSHOT: RetentionClass.REPRODUCIBILITY,
    ArtifactType.DOWNLOAD: RetentionClass.REPRODUCIBILITY,
    ArtifactType.EXPORT: RetentionClass.REPRODUCIBILITY,
    ArtifactType.REPORT: RetentionClass.AUDIT,
    ArtifactType.DIFF: RetentionClass.AUDIT,
    ArtifactType.OTHER: RetentionClass.TEMPORARY,
}


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """Decides whether an artefact may be deleted, by class and age.

    Args:
        temporary_max_age_seconds: The age past which a temporary artefact may be
            deleted.
        reproducibility_max_age_seconds: The age past which a reproducibility
            artefact may be deleted.
    """

    temporary_max_age_seconds: float = 86_400.0
    reproducibility_max_age_seconds: float = 30 * 86_400.0

    def classify(self, artifact_type: ArtifactType) -> RetentionClass:
        """Return the retention class of an artefact type."""
        return _CLASS_BY_TYPE.get(artifact_type, RetentionClass.TEMPORARY)

    def may_delete(self, artifact_type: ArtifactType, age_seconds: float) -> bool:
        """Whether an artefact of this type and age may be deleted.

        Audit-class artefacts always return ``False``. A negative age (a
        timestamp in the future) never permits deletion.
        """
        if age_seconds < 0:
            return False
        retention_class = self.classify(artifact_type)
        if retention_class is RetentionClass.AUDIT:
            return False
        if retention_class is RetentionClass.TEMPORARY:
            return age_seconds >= self.temporary_max_age_seconds
        return age_seconds >= self.reproducibility_max_age_seconds
