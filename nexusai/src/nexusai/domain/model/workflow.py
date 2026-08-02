"""The workflow model: an ordered set of named stages.

A workflow is the recipe the orchestrator follows. It names the stages of a
scraping run in order and records their dependencies, but holds no behaviour --
the stages themselves are supplied by the application layer and delegate to the
engines and services built in earlier phases. Keeping the definition a plain
value means a workflow can be inspected, versioned and validated without running
anything.

Each stage declares what must run before it, so the orchestrator can check the
ordering is coherent (no stage depends on one that comes later, no cycles) before
executing a single step.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StageStatus(Enum):
    """The outcome of running one workflow stage."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"
    FAILED = "failed"


class FailurePolicy(Enum):
    """What a stage's failure does to the workflow.

    Attributes:
        FAIL: The workflow fails; the job goes to ``FAILED``.
        PARTIAL: The workflow finishes in a partial state; the stage's absence is
            tolerated but noted.
        CONTINUE: The failure is a warning; the workflow proceeds unaffected.
    """

    FAIL = "fail"
    PARTIAL = "partial"
    CONTINUE = "continue"


@dataclass(frozen=True, slots=True, kw_only=True)
class StageDefinition:
    """The declaration of one stage within a workflow.

    Attributes:
        name: The stage's identifier, unique within the workflow.
        depends_on: The stages that must succeed before this one runs.
        optional: Whether the stage may be skipped when preconditions are absent.
        failure_policy: What this stage's failure does to the workflow.
        checkpoint_after: Whether to write a checkpoint once this stage succeeds.
    """

    name: str
    depends_on: Sequence[str] = field(default_factory=tuple)
    optional: bool = False
    failure_policy: FailurePolicy = FailurePolicy.FAIL
    checkpoint_after: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "depends_on", tuple(self.depends_on))


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowDefinition:
    """An ordered, dependency-aware set of stages.

    Attributes:
        name: The workflow's name.
        version: The workflow version, recorded on jobs and checkpoints so a
            resume can check the workflow has not changed underneath it.
        stages: The stage declarations, in execution order.
    """

    name: str
    version: str
    stages: Sequence[StageDefinition] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "stages", tuple(self.stages))

    def stage_names(self) -> tuple[str, ...]:
        """Return the stage names in order."""
        return tuple(stage.name for stage in self.stages)

    def stage(self, name: str) -> StageDefinition | None:
        """Return the stage declaration named ``name``, or ``None``."""
        for stage in self.stages:
            if stage.name == name:
                return stage
        return None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "name": self.name,
            "version": self.version,
            "stages": [
                {
                    "name": stage.name,
                    "depends_on": list(stage.depends_on),
                    "optional": stage.optional,
                    "failure_policy": stage.failure_policy.value,
                }
                for stage in self.stages
            ],
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class StageOutcome:
    """The result of executing one stage.

    Attributes:
        name: The stage that ran.
        status: How it ended.
        detail: A short human-readable description.
        error: The error message, when the stage failed.
    """

    name: str
    status: StageStatus
    detail: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "name": self.name,
            "status": self.status.value,
            "detail": self.detail,
            "error": self.error,
        }
