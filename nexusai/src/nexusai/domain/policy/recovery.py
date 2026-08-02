"""Pure recovery decision logic.

A recovery policy turns a failure into a :class:`RecoveryDecision`. The decision
is pure: given the same error and attempt number, a policy always returns the
same verdict, with no sleeping and no retrying of its own. The engine owns those
effects. That separation is what makes recovery testable without a clock or a
network, and what keeps the timing of retries in one place.

The policies here read the exception hierarchy's ``retryable`` flag (Phase 2),
so retryability stays a property of the error type rather than a table each
policy maintains.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from nexusai.domain.errors.exceptions import NexusAIError
from nexusai.domain.model.recovery import RecoveryAction, RecoveryDecision


def _is_retryable(error: Exception) -> bool:
    """Whether the framework considers ``error`` transient and worth retrying."""
    return isinstance(error, NexusAIError) and error.retryable


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Retries retryable failures with exponential backoff, then gives up.

    A non-retryable error is never retried, however many attempts remain: a 404
    will still be a 404 next time. Once the attempts are exhausted, the terminal
    action is applied -- skip by default, so one dead URL does not abort a run of
    thousands, but configurable to abort where a failure means the run is
    compromised.

    Args:
        max_attempts: Total attempts including the first. Two means one retry.
        base_delay_seconds: The first backoff delay; each further retry doubles
            it up to ``max_delay_seconds``.
        max_delay_seconds: The ceiling on any single backoff delay.
        on_exhaustion: The action once retries run out -- skip or abort.
    """

    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 30.0
    on_exhaustion: RecoveryAction = RecoveryAction.SKIP
    name: str = "retry"

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.on_exhaustion not in {RecoveryAction.SKIP, RecoveryAction.ABORT}:
            raise ValueError("on_exhaustion must be SKIP or ABORT")

    def decide(self, error: Exception, attempt: int) -> RecoveryDecision:
        """Return the decision for ``error`` on 1-based ``attempt``."""
        if not _is_retryable(error):
            return RecoveryDecision(
                action=self.on_exhaustion,
                reason=f"{type(error).__name__} is not retryable",
            )
        if attempt >= self.max_attempts:
            return RecoveryDecision(
                action=self.on_exhaustion,
                reason=f"exhausted {self.max_attempts} attempts",
            )
        delay = min(self.base_delay_seconds * (2 ** (attempt - 1)), self.max_delay_seconds)
        return RecoveryDecision.retry(
            delay_seconds=delay, reason=f"retryable {type(error).__name__}, attempt {attempt}"
        )


@dataclass(frozen=True, slots=True)
class SkipPolicy:
    """Skips every failure without retrying.

    For best-effort passes where a failure means "move on", never "try again" or
    "stop everything".
    """

    name: str = "skip"

    def decide(self, error: Exception, attempt: int) -> RecoveryDecision:  # noqa: ARG002
        """Always return a skip decision; the attempt count is irrelevant."""
        return RecoveryDecision.skip(reason=f"skipping {type(error).__name__}")


@dataclass(frozen=True, slots=True)
class AbortPolicy:
    """Aborts on the first failure.

    For runs where any failure invalidates the result, so continuing would waste
    work on an outcome that will be discarded.
    """

    name: str = "abort"

    def decide(self, error: Exception, attempt: int) -> RecoveryDecision:  # noqa: ARG002
        """Always return an abort decision; the attempt count is irrelevant."""
        return RecoveryDecision.abort(reason=f"aborting on {type(error).__name__}")


@dataclass(frozen=True, slots=True)
class PartialSuccessPolicy:
    """Retries transient failures, then accepts a partial result.

    The tolerant counterpart to :class:`RetryPolicy`: it retries what is
    retryable, but when retries are exhausted -- or the error is not retryable --
    it returns ``PARTIAL`` rather than skipping or aborting, signalling that the
    run should keep what it has and record the gap.

    Args:
        max_attempts: Total attempts including the first.
        base_delay_seconds: The first backoff delay; doubles each retry.
        max_delay_seconds: The ceiling on any single backoff delay.
    """

    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 30.0
    name: str = "partial-success"
    _retry: RetryPolicy = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_retry",
            RetryPolicy(
                max_attempts=self.max_attempts,
                base_delay_seconds=self.base_delay_seconds,
                max_delay_seconds=self.max_delay_seconds,
            ),
        )

    def decide(self, error: Exception, attempt: int) -> RecoveryDecision:
        """Retry while possible, otherwise accept a partial result."""
        decision = self._retry.decide(error, attempt)
        if decision.should_retry:
            return decision
        return RecoveryDecision.partial(reason=f"partial result after {type(error).__name__}")
