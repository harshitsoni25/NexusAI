"""Tests for checkpoint integrity, the checkpoint manager, and resume."""

from __future__ import annotations

import dataclasses

import pytest

from application_builders import MemoryCheckpointStore
from nexusai.application.checkpoint.manager import CheckpointManager, ResumeError
from nexusai.domain.model.checkpoint import (
    Checkpoint,
    CheckpointIntegrityError,
    validate_checkpoint,
)
from nexusai.domain.policy.resume_compatibility import (
    CompatibilityLevel,
    ResumeContext,
    assess_compatibility,
)
from nexusai.testing import FrozenClock, SequentialIdGenerator


def _checkpoint(**overrides: object) -> Checkpoint:
    base: dict[str, object] = {
        "checkpoint_id": "c1",
        "job_id": "j1",
        "workflow_version": "1",
        "completed_stage": "extract",
        "next_stage": "process",
    }
    base.update(overrides)
    return Checkpoint(**base)  # type: ignore[arg-type]


class TestCheckpointIntegrity:
    def test_fresh_checkpoint_verifies(self) -> None:
        assert _checkpoint().verify_integrity()

    def test_tampered_checkpoint_fails_verification(self) -> None:
        tampered = dataclasses.replace(_checkpoint(), completed_stage="persist")
        assert not tampered.verify_integrity()

    def test_validate_rejects_tampered(self) -> None:
        tampered = dataclasses.replace(_checkpoint(), completed_stage="persist")
        with pytest.raises(CheckpointIntegrityError):
            validate_checkpoint(tampered)

    def test_validate_rejects_unsupported_version(self) -> None:
        checkpoint = _checkpoint(version=99)
        with pytest.raises(CheckpointIntegrityError):
            validate_checkpoint(checkpoint)

    def test_validate_accepts_sound_checkpoint(self) -> None:
        validate_checkpoint(_checkpoint())


class TestCompatibility:
    def _current(self) -> ResumeContext:
        return ResumeContext(
            workflow_version="1",
            framework_version="0.1.0",
            configuration_ref="cfg",
            schema_version=1,
        )

    def test_matching_is_resumable(self) -> None:
        report = assess_compatibility(
            checkpoint_workflow_version="1",
            checkpoint_framework_version="0.1.0",
            checkpoint_configuration_ref="cfg",
            checkpoint_schema_version=1,
            current=self._current(),
        )
        assert report.resumable
        assert not report.warning_details()

    def test_workflow_change_is_incompatible(self) -> None:
        report = assess_compatibility(
            checkpoint_workflow_version="2",
            checkpoint_framework_version="0.1.0",
            checkpoint_configuration_ref="cfg",
            checkpoint_schema_version=1,
            current=self._current(),
        )
        assert not report.resumable
        assert report.blocking()

    def test_schema_change_is_incompatible(self) -> None:
        report = assess_compatibility(
            checkpoint_workflow_version="1",
            checkpoint_framework_version="0.1.0",
            checkpoint_configuration_ref="cfg",
            checkpoint_schema_version=2,
            current=self._current(),
        )
        assert not report.resumable

    def test_framework_change_is_a_warning(self) -> None:
        report = assess_compatibility(
            checkpoint_workflow_version="1",
            checkpoint_framework_version="0.0.9",
            checkpoint_configuration_ref="cfg",
            checkpoint_schema_version=1,
            current=self._current(),
        )
        assert report.resumable
        assert any(f.level is CompatibilityLevel.WARNING for f in report.findings)


class TestCheckpointManager:
    def _manager(self, store: MemoryCheckpointStore) -> CheckpointManager:
        return CheckpointManager(
            store, clock=FrozenClock(), ids=SequentialIdGenerator(), schema_version=1
        )

    def test_write_persists_a_verifiable_checkpoint(self) -> None:
        store = MemoryCheckpointStore()
        manager = self._manager(store)
        checkpoint = manager.write(
            job_id="j1", workflow_version="1", completed_stage="extract", next_stage="process"
        )
        assert checkpoint.verify_integrity()
        assert store.latest("j1") is not None

    def test_prepare_resume_returns_restart_boundary(self) -> None:
        store = MemoryCheckpointStore()
        manager = self._manager(store)
        manager.write(
            job_id="j1", workflow_version="1", completed_stage="extract", next_stage="process"
        )
        plan = manager.prepare_resume(
            "j1", current_workflow_version="1", current_configuration_ref=None
        )
        assert plan.restart_after == "extract"

    def test_resume_with_no_checkpoint_raises(self) -> None:
        manager = self._manager(MemoryCheckpointStore())
        with pytest.raises(ResumeError):
            manager.prepare_resume(
                "nope", current_workflow_version="1", current_configuration_ref=None
            )

    def test_resume_incompatible_workflow_raises(self) -> None:
        store = MemoryCheckpointStore()
        manager = self._manager(store)
        manager.write(
            job_id="j1", workflow_version="1", completed_stage="extract", next_stage="process"
        )
        with pytest.raises(ResumeError):
            manager.prepare_resume(
                "j1", current_workflow_version="2", current_configuration_ref=None
            )
