"""Tests for the pure recovery policies."""

from __future__ import annotations

import pytest

from nexusai.domain.errors.exceptions import (
    ConfigurationError,
    HttpStatusError,
    NetworkError,
)
from nexusai.domain.model.recovery import RecoveryAction
from nexusai.domain.policy.recovery import (
    AbortPolicy,
    PartialSuccessPolicy,
    RetryPolicy,
    SkipPolicy,
)


def test_retry_backs_off_exponentially_for_retryable_errors() -> None:
    policy = RetryPolicy(max_attempts=4, base_delay_seconds=1.0, max_delay_seconds=100.0)
    delays = [policy.decide(NetworkError("x"), attempt).delay_seconds for attempt in (1, 2, 3)]
    assert delays == [1.0, 2.0, 4.0]


def test_retry_delay_is_capped() -> None:
    policy = RetryPolicy(max_attempts=10, base_delay_seconds=10.0, max_delay_seconds=15.0)
    assert policy.decide(NetworkError("x"), 3).delay_seconds == 15.0


def test_retry_gives_up_after_max_attempts() -> None:
    policy = RetryPolicy(max_attempts=2)
    assert policy.decide(NetworkError("x"), 2).action is RecoveryAction.SKIP


def test_retry_never_retries_non_retryable_error() -> None:
    policy = RetryPolicy(max_attempts=5)
    decision = policy.decide(HttpStatusError("nf", status_code=404), 1)
    assert decision.action is RecoveryAction.SKIP
    assert "not retryable" in decision.reason


def test_retry_can_abort_on_exhaustion() -> None:
    policy = RetryPolicy(max_attempts=1, on_exhaustion=RecoveryAction.ABORT)
    assert policy.decide(NetworkError("x"), 1).action is RecoveryAction.ABORT


def test_retry_rejects_bad_configuration() -> None:
    with pytest.raises(ValueError, match="max_attempts"):
        RetryPolicy(max_attempts=0)
    with pytest.raises(ValueError, match="SKIP or ABORT"):
        RetryPolicy(on_exhaustion=RecoveryAction.RETRY)


def test_skip_policy_always_skips() -> None:
    assert SkipPolicy().decide(NetworkError("x"), 1).action is RecoveryAction.SKIP


def test_abort_policy_always_aborts() -> None:
    assert AbortPolicy().decide(NetworkError("x"), 1).action is RecoveryAction.ABORT


def test_partial_policy_retries_then_accepts_partial() -> None:
    policy = PartialSuccessPolicy(max_attempts=2, base_delay_seconds=0.0)
    assert policy.decide(NetworkError("x"), 1).action is RecoveryAction.RETRY
    assert policy.decide(NetworkError("x"), 2).action is RecoveryAction.PARTIAL


def test_partial_policy_accepts_partial_for_non_retryable() -> None:
    policy = PartialSuccessPolicy()
    decision = policy.decide(ConfigurationError("bad"), 1)
    assert decision.action is RecoveryAction.PARTIAL


def test_decision_predicates() -> None:
    policy = RetryPolicy(max_attempts=3, base_delay_seconds=0.0)
    retry = policy.decide(NetworkError("x"), 1)
    skip = SkipPolicy().decide(NetworkError("x"), 1)
    assert retry.should_retry is True
    assert skip.is_terminal is True
