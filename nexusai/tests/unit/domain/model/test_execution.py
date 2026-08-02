"""Tests for ExecutionInfo and ConfigurationSnapshot."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from nexusai.domain.model.execution import (
    ConfigurationSnapshot,
    ExecutionInfo,
    ExecutionStatus,
)
from nexusai.shared.identifiers import CorrelationId

_T0 = datetime(2026, 1, 1, tzinfo=UTC)
_T1 = _T0 + timedelta(seconds=5)


def _info() -> ExecutionInfo:
    return ExecutionInfo(correlation_id=CorrelationId("c1"))


def test_terminal_status_flag() -> None:
    assert ExecutionStatus.SUCCEEDED.is_terminal
    assert ExecutionStatus.FAILED.is_terminal
    assert ExecutionStatus.CANCELLED.is_terminal
    assert not ExecutionStatus.PENDING.is_terminal
    assert not ExecutionStatus.RUNNING.is_terminal


def test_pending_has_no_duration() -> None:
    assert _info().duration_seconds is None


def test_lifecycle_transitions_are_immutable() -> None:
    pending = _info()
    running = pending.started(_T0)
    done = running.finished(ExecutionStatus.SUCCEEDED, _T1)
    assert pending.status is ExecutionStatus.PENDING
    assert running.status is ExecutionStatus.RUNNING
    assert done.status is ExecutionStatus.SUCCEEDED
    assert done.duration_seconds == 5.0


def test_finished_rejects_non_terminal_status() -> None:
    with pytest.raises(ValueError, match="not a terminal status"):
        _info().started(_T0).finished(ExecutionStatus.RUNNING, _T1)


def test_with_attributes_merges() -> None:
    info = _info().with_attributes(target="x").with_attributes(count=3)
    assert info.attributes == {"target": "x", "count": 3}


def test_duration_none_when_only_started() -> None:
    assert _info().started(_T0).duration_seconds is None


def test_serialisation_includes_derived_duration() -> None:
    payload = _info().started(_T0).finished(ExecutionStatus.FAILED, _T1).to_dict()
    assert payload["status"] == "failed"
    assert payload["duration_seconds"] == 5.0
    assert payload["correlation_id"] == "c1"


def test_attributes_copied_defensively() -> None:
    attrs = {"a": 1}
    info = ExecutionInfo(correlation_id=CorrelationId("c"), attributes=attrs)
    attrs["a"] = 99
    assert info.attributes == {"a": 1}


def test_configuration_snapshot_origin_lookup_and_serialisation() -> None:
    snap = ConfigurationSnapshot(
        values={"http": {"timeout": 30}},
        origins={"http.timeout": "environment"},
    )
    assert snap.origin_of("http.timeout") == "environment"
    assert snap.origin_of("absent") is None
    assert snap.to_dict() == {
        "values": {"http": {"timeout": 30}},
        "origins": {"http.timeout": "environment"},
    }


def test_configuration_snapshot_copies_inputs() -> None:
    values = {"a": 1}
    origins = {"a": "defaults"}
    snap = ConfigurationSnapshot(values=values, origins=origins)
    values["a"] = 2
    origins["a"] = "cli"
    assert snap.values == {"a": 1}
    assert snap.origins == {"a": "defaults"}
