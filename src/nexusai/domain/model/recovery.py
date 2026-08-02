"""The decision a recovery policy returns when retrieval fails.

A recovery policy converts a failure and its attempt count into an *action*:
retry after a delay, skip this item, abort the run, or accept a partial result.
This module holds the vocabulary of that decision; the policies that make it are
pure logic in :mod:`nexusai.domain.policy.recovery`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RecoveryAction(Enum):
    """What to do about a failure."""

    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"
    PARTIAL = "partial"


@dataclass(frozen=True, slots=True, kw_only=True)
class RecoveryDecision:
    """A recovery policy's verdict on a single failure.

    Attributes:
        action: What the caller should do next.
        delay_seconds: How long to wait before a retry. Zero for non-retry
            actions.
        reason: A human-readable explanation, carried into logs so that "why did
            this abort?" is answerable after the fact.
    """

    action: RecoveryAction
    delay_seconds: float = 0.0
    reason: str = ""

    @property
    def should_retry(self) -> bool:
        """Whether the action is to retry."""
        return self.action is RecoveryAction.RETRY

    @property
    def is_terminal(self) -> bool:
        """Whether the action ends processing of the item (skip or abort)."""
        return self.action in {RecoveryAction.SKIP, RecoveryAction.ABORT}

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "action": self.action.value,
            "delay_seconds": self.delay_seconds,
            "reason": self.reason,
        }

    @classmethod
    def retry(cls, delay_seconds: float, reason: str = "") -> RecoveryDecision:
        """Return a retry decision with a backoff delay."""
        return cls(action=RecoveryAction.RETRY, delay_seconds=delay_seconds, reason=reason)

    @classmethod
    def skip(cls, reason: str = "") -> RecoveryDecision:
        """Return a skip decision."""
        return cls(action=RecoveryAction.SKIP, reason=reason)

    @classmethod
    def abort(cls, reason: str = "") -> RecoveryDecision:
        """Return an abort decision."""
        return cls(action=RecoveryAction.ABORT, reason=reason)

    @classmethod
    def partial(cls, reason: str = "") -> RecoveryDecision:
        """Return a partial-success decision."""
        return cls(action=RecoveryAction.PARTIAL, reason=reason)
