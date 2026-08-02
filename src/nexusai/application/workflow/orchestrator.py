"""The workflow orchestrator: runs stages, coordinates, but does no work itself.

The orchestrator is a conductor. It resolves the workflow, checks the stage
dependencies form a coherent order, then runs each stage in turn -- threading the
context through, honouring cancellation between stages, writing a checkpoint after
the stages that ask for one, and recording an outcome per stage. When every stage
has run (or failed), it applies the partial-failure policy to decide the job's
final state.

What the orchestrator never does is the actual scraping. Retrieval, extraction,
processing, persistence, export and reporting all live behind the stages, which
delegate to the engines and services of earlier phases. The orchestrator only
decides *order, coordination and outcome* -- if a line here looked like it was
parsing HTML or writing a row, it would be in the wrong place.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from nexusai.application.runtime.cancellation import CancelledError
from nexusai.application.runtime.context import ExecutionContext
from nexusai.application.workflow.stage import WorkflowStage, Workspace
from nexusai.domain.errors.exceptions import NexusAIError
from nexusai.domain.model.job import JobState
from nexusai.domain.model.workflow import (
    StageOutcome,
    StageStatus,
    WorkflowDefinition,
)
from nexusai.domain.policy.partial_failure import resolve_final_state
from nexusai.domain.ports.observability import Logger

CheckpointCallback = Callable[[str, ExecutionContext], str]
"""Called after a checkpointed stage; returns the checkpoint reference to record."""


class WorkflowValidationError(NexusAIError):
    """A workflow definition is incoherent: a missing or out-of-order dependency."""


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowResult:
    """The outcome of running a workflow."""

    final_state: JobState
    context: ExecutionContext
    outcomes: Sequence[StageOutcome] = field(default_factory=tuple)
    warnings: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "outcomes", tuple(self.outcomes))
        object.__setattr__(self, "warnings", tuple(self.warnings))


def validate_workflow(definition: WorkflowDefinition, stages: Mapping[str, WorkflowStage]) -> None:
    """Check every stage exists and no stage depends on a later one.

    Raises:
        WorkflowValidationError: If a stage is unimplemented, or a dependency is
            unknown or declared after the stage that needs it.
    """
    seen: set[str] = set()
    for definition_stage in definition.stages:
        if definition_stage.name not in stages:
            raise WorkflowValidationError(
                "Workflow stage has no implementation", stage=definition_stage.name
            )
        for dependency in definition_stage.depends_on:
            if dependency not in definition.stage_names():
                raise WorkflowValidationError(
                    "Stage depends on an unknown stage",
                    stage=definition_stage.name,
                    dependency=dependency,
                )
            if dependency not in seen:
                raise WorkflowValidationError(
                    "Stage depends on a later stage",
                    stage=definition_stage.name,
                    dependency=dependency,
                )
        seen.add(definition_stage.name)


class WorkflowOrchestrator:
    """Executes a workflow's stages in order, coordinating without doing the work.

    Args:
        definition: The workflow to run.
        stages: The stage implementations, keyed by name.
        logger: For lifecycle logging.
        on_checkpoint: Called after a stage whose definition sets
            ``checkpoint_after``; receives the completed stage name and the
            current context, and returns a checkpoint reference to record.
    """

    def __init__(
        self,
        definition: WorkflowDefinition,
        stages: Mapping[str, WorkflowStage],
        *,
        logger: Logger,
        on_checkpoint: CheckpointCallback | None = None,
    ) -> None:
        validate_workflow(definition, stages)
        self._definition = definition
        self._stages = dict(stages)
        self._logger = logger
        self._on_checkpoint = on_checkpoint

    def run(
        self,
        context: ExecutionContext,
        workspace: Workspace,
        *,
        start_after: str | None = None,
    ) -> WorkflowResult:
        """Run the workflow from the start, or resume after ``start_after``.

        Args:
            context: The initial (or resumed) execution context.
            workspace: The working memory shared across stages.
            start_after: When resuming, the last completed stage; stages up to and
                including it are skipped.
        """
        outcomes: list[StageOutcome] = []
        current = context
        skipping = start_after is not None

        for definition_stage in self._definition.stages:
            name = definition_stage.name
            if skipping:
                outcomes.append(
                    StageOutcome(name=name, status=StageStatus.SKIPPED, detail="resumed past")
                )
                if name == start_after:
                    skipping = False
                continue

            try:
                current.cancellation.raise_if_cancelled()
            except CancelledError:
                self._logger.info("workflow.cancelled", stage=name)
                return WorkflowResult(
                    final_state=JobState.CANCELLED,
                    context=current,
                    outcomes=outcomes,
                    warnings=("cancelled before stage " + name,),
                )

            stage = self._stages[name]
            if not stage.can_run(current, workspace):
                outcomes.append(
                    StageOutcome(
                        name=name, status=StageStatus.SKIPPED, detail="preconditions not met"
                    )
                )
                continue

            outcome, current = self._run_stage(stage, definition_stage.name, current, workspace)
            outcomes.append(outcome)
            if outcome.status is StageStatus.SUCCEEDED and definition_stage.checkpoint_after:
                current = self._checkpoint(name, current)

        verdict = resolve_final_state(self._definition, outcomes)
        return WorkflowResult(
            final_state=verdict.state,
            context=current,
            outcomes=outcomes,
            warnings=verdict.warnings,
        )

    def _run_stage(
        self,
        stage: WorkflowStage,
        name: str,
        context: ExecutionContext,
        workspace: Workspace,
    ) -> tuple[StageOutcome, ExecutionContext]:
        self._logger.info("workflow.stage.start", stage=name)
        try:
            updated = stage.execute(context, workspace)
        except NexusAIError as error:
            self._logger.warning("workflow.stage.failed", stage=name, error=str(error))
            return (
                StageOutcome(name=name, status=StageStatus.FAILED, error=str(error)),
                context,
            )
        self._logger.info("workflow.stage.done", stage=name)
        return StageOutcome(name=name, status=StageStatus.SUCCEEDED), updated

    def _checkpoint(self, stage: str, context: ExecutionContext) -> ExecutionContext:
        if self._on_checkpoint is None:
            return context
        checkpoint_ref = self._on_checkpoint(stage, context)
        return context.with_checkpoint(checkpoint_ref)
