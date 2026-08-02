"""Pure policy for whether a checkpoint may be resumed.

Not every difference between a checkpoint and the current world makes resume
impossible, and treating them all as fatal would make resume useless; treating
them all as fine would make it dangerous. So this policy classifies each
difference into one of three levels -- compatible, warning, incompatible -- and a
resume proceeds only when nothing is incompatible, carrying any warnings forward.

The classification is deliberately conservative where correctness is at stake: a
changed workflow version or persistence schema is incompatible, because the
meaning of a stage or a stored row may have changed, while a changed framework
patch version is a warning and an unchanged configuration is fully compatible.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum


class CompatibilityLevel(Enum):
    """How a difference between checkpoint and current state affects resume."""

    COMPATIBLE = "compatible"
    WARNING = "warning"
    INCOMPATIBLE = "incompatible"


@dataclass(frozen=True, slots=True, kw_only=True)
class CompatibilityFinding:
    """One difference and how it bears on resume."""

    field: str
    level: CompatibilityLevel
    detail: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CompatibilityReport:
    """The overall verdict on resuming a checkpoint."""

    findings: Sequence[CompatibilityFinding] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "findings", tuple(self.findings))

    @property
    def resumable(self) -> bool:
        """Whether nothing incompatible was found."""
        return not any(f.level is CompatibilityLevel.INCOMPATIBLE for f in self.findings)

    def warning_details(self) -> list[str]:
        """Return the details of warning-level findings."""
        return [
            f"{f.field}: {f.detail}" for f in self.findings if f.level is CompatibilityLevel.WARNING
        ]

    def blocking(self) -> list[str]:
        """Return the details of incompatible findings that block resume."""
        return [
            f"{f.field}: {f.detail}"
            for f in self.findings
            if f.level is CompatibilityLevel.INCOMPATIBLE
        ]


@dataclass(frozen=True, slots=True, kw_only=True)
class ResumeContext:
    """The current-world identities a checkpoint is checked against."""

    workflow_version: str
    framework_version: str
    configuration_ref: str | None
    schema_version: int


def assess_compatibility(
    *,
    checkpoint_workflow_version: str,
    checkpoint_framework_version: str,
    checkpoint_configuration_ref: str | None,
    checkpoint_schema_version: int,
    current: ResumeContext,
) -> CompatibilityReport:
    """Classify each difference between a checkpoint and the current world."""
    findings: list[CompatibilityFinding] = []

    if checkpoint_workflow_version != current.workflow_version:
        findings.append(
            CompatibilityFinding(
                field="workflow_version",
                level=CompatibilityLevel.INCOMPATIBLE,
                detail=(
                    f"checkpoint {checkpoint_workflow_version} != current "
                    f"{current.workflow_version}"
                ),
            )
        )
    if checkpoint_schema_version != current.schema_version:
        findings.append(
            CompatibilityFinding(
                field="schema_version",
                level=CompatibilityLevel.INCOMPATIBLE,
                detail=(
                    f"checkpoint {checkpoint_schema_version} != current "
                    f"{current.schema_version}"
                ),
            )
        )
    if checkpoint_framework_version != current.framework_version:
        findings.append(
            CompatibilityFinding(
                field="framework_version",
                level=CompatibilityLevel.WARNING,
                detail=(
                    f"checkpoint {checkpoint_framework_version} != current "
                    f"{current.framework_version}"
                ),
            )
        )
    if (
        checkpoint_configuration_ref is not None
        and checkpoint_configuration_ref != current.configuration_ref
    ):
        findings.append(
            CompatibilityFinding(
                field="configuration_ref",
                level=CompatibilityLevel.WARNING,
                detail="effective configuration changed since checkpoint",
            )
        )
    return CompatibilityReport(findings=findings)
