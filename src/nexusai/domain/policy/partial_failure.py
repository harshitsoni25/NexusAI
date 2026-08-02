"""Pure policy mapping stage outcomes to a job's final state.

A workflow rarely ends in a clean binary. Some pages fail but enough succeed;
validation warns but does not fail; an optional export breaks after the data is
safely persisted. This policy turns the collection of stage outcomes into one job
state, honouring each stage's declared failure policy, so that "materially
incomplete" never masquerades as "completed".

The rule: any stage whose failure policy is ``FAIL`` failing sends the job to
``FAILED``; failing stages whose policy is ``PARTIAL`` send it to ``PARTIAL``;
``CONTINUE`` failures are warnings only. A run with no failures completes.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from nexusai.domain.model.job import JobState
from nexusai.domain.model.workflow import (
    FailurePolicy,
    StageOutcome,
    StageStatus,
    WorkflowDefinition,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class OutcomeVerdict:
    """The job state a set of stage outcomes implies, with any warnings."""

    state: JobState
    warnings: Sequence[str] = field(default_factory=tuple)
    failed_stages: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "failed_stages", tuple(self.failed_stages))


def resolve_final_state(
    workflow: WorkflowDefinition, outcomes: Sequence[StageOutcome]
) -> OutcomeVerdict:
    """Return the job state implied by ``outcomes`` under ``workflow``'s policies."""
    warnings: list[str] = []
    failed: list[str] = []
    hard_failure = False
    partial = False

    for outcome in outcomes:
        if outcome.status is not StageStatus.FAILED:
            continue
        failed.append(outcome.name)
        stage = workflow.stage(outcome.name)
        policy = stage.failure_policy if stage else FailurePolicy.FAIL
        if policy is FailurePolicy.FAIL:
            hard_failure = True
            warnings.append(f"stage {outcome.name!r} failed: {outcome.error or ''}")
        elif policy is FailurePolicy.PARTIAL:
            partial = True
            warnings.append(f"optional stage {outcome.name!r} failed")
        else:
            warnings.append(f"stage {outcome.name!r} failed but continued")

    if hard_failure:
        state = JobState.FAILED
    elif partial:
        state = JobState.PARTIAL
    else:
        state = JobState.COMPLETED
    return OutcomeVerdict(state=state, warnings=warnings, failed_stages=failed)
