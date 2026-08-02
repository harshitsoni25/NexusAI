"""The job state machine: which transitions are allowed, as one table.

State changes are the most safety-critical operation in the application layer --
a job wrongly moved to ``COMPLETED`` hides a failure; one wrongly left
``RUNNING`` blocks a resume. So the rules live here, pure and in one place, rather
than as scattered assignments. The machine answers one question -- may a job move
from state A to state B? -- and the job manager routes every transition through
it.

The transition table encodes the lifecycle: a job is created, queued, runs, and
then either completes, partially completes, fails, is cancelled, or pauses for
later resume. Terminal states admit nothing further; ``PAUSED`` is the one
non-terminal resting state, from which a resume re-enters ``RUNNING``.
"""

from __future__ import annotations

from nexusai.domain.errors.exceptions import NexusAIError
from nexusai.domain.model.job import JobState

_TRANSITIONS: dict[JobState, frozenset[JobState]] = {
    JobState.CREATED: frozenset({JobState.QUEUED, JobState.RUNNING, JobState.CANCELLED}),
    JobState.QUEUED: frozenset({JobState.RUNNING, JobState.CANCELLED}),
    JobState.RUNNING: frozenset(
        {
            JobState.PAUSED,
            JobState.PARTIAL,
            JobState.COMPLETED,
            JobState.FAILED,
            JobState.CANCELLED,
        }
    ),
    JobState.PAUSED: frozenset({JobState.RUNNING, JobState.CANCELLED}),
    JobState.PARTIAL: frozenset(),
    JobState.COMPLETED: frozenset(),
    JobState.FAILED: frozenset(),
    JobState.CANCELLED: frozenset(),
}

_TERMINAL: frozenset[JobState] = frozenset(
    {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED, JobState.PARTIAL}
)
_RECOVERABLE: frozenset[JobState] = frozenset({JobState.PAUSED})


class InvalidTransitionError(NexusAIError):
    """A job was asked to make a transition its current state does not permit."""


def can_transition(source: JobState, target: JobState) -> bool:
    """Whether a job may move from ``source`` to ``target``."""
    return target in _TRANSITIONS[source]


def ensure_transition(source: JobState, target: JobState) -> None:
    """Raise if a job may not move from ``source`` to ``target``.

    Raises:
        InvalidTransitionError: If the transition is not permitted.
    """
    if not can_transition(source, target):
        raise InvalidTransitionError(
            "Illegal job state transition",
            source=source.value,
            target=target.value,
        )


def is_terminal(state: JobState) -> bool:
    """Whether ``state`` admits no further transition."""
    return state in _TERMINAL


def is_recoverable(state: JobState) -> bool:
    """Whether a job in ``state`` can be resumed."""
    return state in _RECOVERABLE


def allowed_transitions(state: JobState) -> frozenset[JobState]:
    """Return the states reachable from ``state`` in one step."""
    return _TRANSITIONS[state]
