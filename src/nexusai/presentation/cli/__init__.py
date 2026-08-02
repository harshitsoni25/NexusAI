"""The command line interface.

The framework's primary user-facing surface. Commands translate input into a use
case invocation and render the result; they contain no business logic.
"""

from __future__ import annotations

from nexusai.presentation.cli.app import app, run
from nexusai.presentation.cli.exit_codes import ExitCode

__all__ = ["ExitCode", "app", "run"]
