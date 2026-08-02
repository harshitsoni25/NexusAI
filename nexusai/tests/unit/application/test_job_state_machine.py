"""Tests for the job model and its state machine."""

from __future__ import annotations

import pytest

from nexusai.domain.model.job import Job, JobState
from nexusai.domain.policy.job_state_machine import (
    InvalidTransitionError,
    allowed_transitions,
    can_transition,
    ensure_transition,
    is_recoverable,
    is_terminal,
)


class TestTransitions:
    @pytest.mark.parametrize(
        ("source", "target"),
        [
            (JobState.CREATED, JobState.QUEUED),
            (JobState.CREATED, JobState.RUNNING),
            (JobState.QUEUED, JobState.RUNNING),
            (JobState.RUNNING, JobState.PAUSED),
            (JobState.RUNNING, JobState.COMPLETED),
            (JobState.RUNNING, JobState.PARTIAL),
            (JobState.RUNNING, JobState.FAILED),
            (JobState.RUNNING, JobState.CANCELLED),
            (JobState.PAUSED, JobState.RUNNING),
        ],
    )
    def test_valid_transitions_are_permitted(self, source: JobState, target: JobState) -> None:
        assert can_transition(source, target)
        ensure_transition(source, target)

    @pytest.mark.parametrize(
        ("source", "target"),
        [
            (JobState.COMPLETED, JobState.RUNNING),
            (JobState.FAILED, JobState.RUNNING),
            (JobState.CANCELLED, JobState.RUNNING),
            (JobState.CREATED, JobState.COMPLETED),
            (JobState.PARTIAL, JobState.RUNNING),
            (JobState.RUNNING, JobState.QUEUED),
        ],
    )
    def test_invalid_transitions_are_rejected(self, source: JobState, target: JobState) -> None:
        assert not can_transition(source, target)
        with pytest.raises(InvalidTransitionError):
            ensure_transition(source, target)

    def test_terminal_states(self) -> None:
        for state in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED, JobState.PARTIAL):
            assert is_terminal(state)
        assert not is_terminal(JobState.RUNNING)

    def test_only_paused_is_recoverable(self) -> None:
        assert is_recoverable(JobState.PAUSED)
        assert not is_recoverable(JobState.RUNNING)
        assert not is_recoverable(JobState.FAILED)

    def test_terminal_states_have_no_outgoing_transitions(self) -> None:
        assert allowed_transitions(JobState.COMPLETED) == frozenset()


class TestJobModel:
    def test_job_is_terminal_reflects_state(self) -> None:
        assert not Job(job_id="j", target="t").is_terminal
        assert Job(job_id="j", target="t", state=JobState.COMPLETED).is_terminal

    def test_to_dict_round_trips_key_fields(self) -> None:
        job = Job(job_id="j", target="https://x", export_refs=("e1",))
        data = job.to_dict()
        assert data["job_id"] == "j"
        assert data["export_refs"] == ["e1"]
        assert data["state"] == "created"
