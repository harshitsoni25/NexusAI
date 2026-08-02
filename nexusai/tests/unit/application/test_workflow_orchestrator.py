"""Tests for workflow validation, the orchestrator, and the stages."""

from __future__ import annotations

import pytest

from nexusai.application.runtime.cancellation import CancellationToken
from nexusai.application.runtime.context import ExecutionContext
from nexusai.application.workflow.orchestrator import (
    WorkflowOrchestrator,
    WorkflowValidationError,
    validate_workflow,
)
from nexusai.application.workflow.stage import Workspace
from nexusai.domain.errors.exceptions import NexusAIError
from nexusai.domain.model.job import JobState
from nexusai.domain.model.workflow import (
    FailurePolicy,
    StageDefinition,
    StageStatus,
    WorkflowDefinition,
)
from nexusai.testing import RecordingLogger


class _Stage:
    def __init__(self, name: str, *, fail: bool = False, runnable: bool = True) -> None:
        self.name = name
        self._fail = fail
        self._runnable = runnable

    def can_run(self, context: ExecutionContext, workspace: Workspace) -> bool:
        return self._runnable

    def execute(self, context: ExecutionContext, workspace: Workspace) -> ExecutionContext:
        if self._fail:
            raise NexusAIError("stage failed")
        workspace.put(self.name, True)
        return context


def _context(*, token: CancellationToken | None = None) -> ExecutionContext:
    return ExecutionContext(
        job_id="j1",
        correlation_id="c1",
        workflow_version="1",
        target="https://x",
        cancellation=token or CancellationToken(),
    )


class TestValidateWorkflow:
    def test_missing_implementation_is_rejected(self) -> None:
        workflow = WorkflowDefinition(name="w", version="1", stages=[StageDefinition(name="a")])
        with pytest.raises(WorkflowValidationError):
            validate_workflow(workflow, {})

    def test_unknown_dependency_is_rejected(self) -> None:
        workflow = WorkflowDefinition(
            name="w",
            version="1",
            stages=[StageDefinition(name="a", depends_on=["ghost"])],
        )
        with pytest.raises(WorkflowValidationError):
            validate_workflow(workflow, {"a": _Stage("a")})

    def test_later_dependency_is_rejected(self) -> None:
        workflow = WorkflowDefinition(
            name="w",
            version="1",
            stages=[StageDefinition(name="a", depends_on=["b"]), StageDefinition(name="b")],
        )
        with pytest.raises(WorkflowValidationError):
            validate_workflow(workflow, {"a": _Stage("a"), "b": _Stage("b")})


class TestOrchestrator:
    def _workflow(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            name="w",
            version="1",
            stages=[
                StageDefinition(name="a"),
                StageDefinition(name="b", depends_on=["a"], checkpoint_after=True),
                StageDefinition(
                    name="c", depends_on=["b"], optional=True, failure_policy=FailurePolicy.PARTIAL
                ),
            ],
        )

    def test_all_stages_succeed_completes(self) -> None:
        stages = {n: _Stage(n) for n in ("a", "b", "c")}
        orch = WorkflowOrchestrator(self._workflow(), stages, logger=RecordingLogger())
        result = orch.run(_context(), Workspace())
        assert result.final_state is JobState.COMPLETED
        assert [o.status for o in result.outcomes] == [StageStatus.SUCCEEDED] * 3

    def test_partial_policy_failure_yields_partial(self) -> None:
        stages = {"a": _Stage("a"), "b": _Stage("b"), "c": _Stage("c", fail=True)}
        orch = WorkflowOrchestrator(self._workflow(), stages, logger=RecordingLogger())
        result = orch.run(_context(), Workspace())
        assert result.final_state is JobState.PARTIAL

    def test_hard_failure_fails_the_job(self) -> None:
        stages = {"a": _Stage("a", fail=True), "b": _Stage("b"), "c": _Stage("c")}
        orch = WorkflowOrchestrator(self._workflow(), stages, logger=RecordingLogger())
        result = orch.run(_context(), Workspace())
        assert result.final_state is JobState.FAILED

    def test_stage_that_cannot_run_is_skipped(self) -> None:
        stages = {"a": _Stage("a"), "b": _Stage("b", runnable=False), "c": _Stage("c")}
        orch = WorkflowOrchestrator(self._workflow(), stages, logger=RecordingLogger())
        result = orch.run(_context(), Workspace())
        statuses = {o.name: o.status for o in result.outcomes}
        assert statuses["b"] is StageStatus.SKIPPED

    def test_checkpoint_callback_fires_after_marked_stage(self) -> None:
        calls: list[str] = []
        stages = {n: _Stage(n) for n in ("a", "b", "c")}

        def record(stage: str, ctx: ExecutionContext) -> str:
            calls.append(stage)
            return "cp-1"

        orch = WorkflowOrchestrator(
            self._workflow(),
            stages,
            logger=RecordingLogger(),
            on_checkpoint=record,
        )
        result = orch.run(_context(), Workspace())
        assert calls == ["b"]
        assert result.context.checkpoint_ref == "cp-1"

    def test_cancellation_before_a_stage_stops_the_run(self) -> None:
        token = CancellationToken()
        token.cancel()
        stages = {n: _Stage(n) for n in ("a", "b", "c")}
        orch = WorkflowOrchestrator(self._workflow(), stages, logger=RecordingLogger())
        result = orch.run(_context(token=token), Workspace())
        assert result.final_state is JobState.CANCELLED

    def test_resume_skips_completed_stages(self) -> None:
        stages = {n: _Stage(n) for n in ("a", "b", "c")}
        orch = WorkflowOrchestrator(self._workflow(), stages, logger=RecordingLogger())
        result = orch.run(_context(), Workspace(), start_after="b")
        statuses = {o.name: o.status for o in result.outcomes}
        assert statuses["a"] is StageStatus.SKIPPED
        assert statuses["b"] is StageStatus.SKIPPED
        assert statuses["c"] is StageStatus.SUCCEEDED


class TestWorkspace:
    def test_require_raises_when_absent(self) -> None:
        with pytest.raises(KeyError):
            Workspace().require("missing")

    def test_put_and_get(self) -> None:
        workspace = Workspace()
        workspace.put("k", 1)
        assert workspace.get("k") == 1
        assert workspace.has("k")
