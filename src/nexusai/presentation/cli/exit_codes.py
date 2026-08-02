"""Process exit codes.

Exit codes are part of the framework's public contract: schedulers and CI
systems act on them. Distinguishing configuration failure from execution failure
lets an operator tell "I typed something wrong" from "the run went badly"
without reading the log.
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Process exit codes returned by the command line interface."""

    SUCCESS = 0
    """The command completed."""

    FAILURE = 1
    """The command failed for a reason within the framework's control."""

    CONFIGURATION_ERROR = 2
    """Configuration was missing, malformed, or invalid."""

    INVALID_INPUT = 3
    """A command argument or option was invalid."""

    PARTIAL = 4
    """The run finished with a materially complete but partial result."""

    POLICY_REJECTED = 5
    """A preflight or responsible-use policy refused the operation."""

    VALIDATION_FAILURE = 6
    """A dataset failed validation."""

    EXECUTION_FAILURE = 7
    """A workflow execution failed."""

    RESUME_INCOMPATIBLE = 8
    """A checkpoint could not be safely resumed."""

    DEPENDENCY_FAILURE = 9
    """A required dependency or environment check failed."""

    INTERNAL_ERROR = 70
    """An invariant of the framework itself was violated. Always a defect."""
