"""Console output and the boundary where framework errors become exit codes."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from rich.console import Console
from rich.panel import Panel

from nexusai.domain.errors import (
    ConfigurationError,
    InternalError,
    NexusAIError,
    PluginError,
    ValidationError,
)
from nexusai.presentation.cli.exit_codes import ExitCode

console = Console()
"""Standard output, for results."""

error_console = Console(stderr=True)
"""Standard error, so that diagnostics never contaminate piped output."""


def render_error(error: NexusAIError) -> None:
    """Present a framework error as a titled panel.

    The message is printed as written, because framework errors are composed to
    be read by an operator: they already name the offending key, its source and
    what was expected instead.
    """
    error_console.print(
        Panel(
            str(error),
            title=f"[bold red]{type(error).__name__}[/bold red]",
            subtitle=f"category: {error.category.value}",
            border_style="red",
        )
    )


def exit_code_for(error: NexusAIError) -> ExitCode:
    """Map an error to the process exit code it should produce.

    The mapping is deliberately by *category* of failure, so an operator or a
    scheduler can act on the code without reading the log: a resume that could not
    proceed, a dataset that failed validation and a plugin that was rejected each
    get their own code, distinct from a generic failure.
    """
    from nexusai.application.checkpoint.manager import ResumeError
    from nexusai.application.workflow.orchestrator import WorkflowValidationError

    if isinstance(error, ConfigurationError):
        return ExitCode.CONFIGURATION_ERROR
    if isinstance(error, ResumeError):
        return ExitCode.RESUME_INCOMPATIBLE
    if isinstance(error, ValidationError):
        return ExitCode.VALIDATION_FAILURE
    if isinstance(error, PluginError):
        return ExitCode.DEPENDENCY_FAILURE
    if isinstance(error, WorkflowValidationError):
        return ExitCode.EXECUTION_FAILURE
    if isinstance(error, InternalError):
        return ExitCode.INTERNAL_ERROR
    return ExitCode.FAILURE


@contextmanager
def error_boundary() -> Iterator[None]:
    """Turn a framework error into a rendered message and an exit code.

    Applied once, around the whole application, rather than in every command.
    Centralising it means a new command cannot forget to handle errors, and
    there is exactly one place that decides how a failure is presented.

    Only ``NexusAIError`` is caught. An unexpected exception propagates with
    its traceback intact: a stack trace is precisely what is wanted when the
    framework itself has a defect, and section 41 forbids swallowing it.
    """
    try:
        yield
    except NexusAIError as error:
        render_error(error)
        raise SystemExit(int(exit_code_for(error))) from error
