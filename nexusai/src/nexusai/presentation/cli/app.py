"""The command line application.

Commands are registered explicitly rather than discovered, so that reading this
module tells you the entire surface of the CLI. Each command module exposes a
``register`` function, which keeps the wiring here to one line per command and
lets a command own its own options.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import click
import typer
from typer.core import TyperGroup

from nexusai.__about__ import __version__
from nexusai.domain.errors import NexusAIError
from nexusai.presentation.cli.commands import analyze as analyze_command
from nexusai.presentation.cli.commands import benchmark as benchmark_command
from nexusai.presentation.cli.commands import config as config_command
from nexusai.presentation.cli.commands import datasets as datasets_command
from nexusai.presentation.cli.commands import diagnose as diagnose_command
from nexusai.presentation.cli.commands import doctor as doctor_command
from nexusai.presentation.cli.commands import jobs as jobs_command
from nexusai.presentation.cli.commands import plugins as plugins_command
from nexusai.presentation.cli.commands import schedule as schedule_command
from nexusai.presentation.cli.commands import scrape as scrape_command
from nexusai.presentation.cli.commands import stats as stats_command
from nexusai.presentation.cli.commands import version as version_command
from nexusai.presentation.cli.exit_codes import ExitCode
from nexusai.presentation.cli.rendering.console import (
    console,
    error_boundary,
    exit_code_for,
    render_error,
)
from nexusai.presentation.cli.state import CliState, resolve_overrides


class _ErrorHandlingGroup(TyperGroup):
    """Converts framework errors into rendered output and an exit code.

    Attached to the root group rather than wrapped around individual commands,
    so the behaviour applies to every command, every subgroup and the global
    callback alike -- including when the application is invoked programmatically
    rather than through the console script.
    """

    def invoke(self, ctx: click.Context) -> Any:
        """Run the selected command, translating framework and usage errors."""
        try:
            return super().invoke(ctx)
        except NexusAIError as error:
            render_error(error)
            raise typer.Exit(code=int(exit_code_for(error))) from error
        except click.UsageError as error:
            # Bad input or misuse. Render click's own message, but exit with the
            # framework's documented invalid-input code rather than click's
            # default, so the CLI's exit-code contract stays consistent.
            error.show()
            raise typer.Exit(code=int(ExitCode.INVALID_INPUT)) from error


app = typer.Typer(
    cls=_ErrorHandlingGroup,
    name="nexusai",
    help=(
        "Nexus AI -- an enterprise framework for collecting, validating, "
        "monitoring and exporting publicly available web data."
    ),
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode="rich",
)

version_command.register(app)
config_command.register(app)
plugins_command.register(app)
diagnose_command.register(app)
doctor_command.register(app)
analyze_command.register(app)
scrape_command.register(app)
jobs_command.register(app)
stats_command.register(app)
schedule_command.register(app)
datasets_command.register(app)
benchmark_command.register(app)
scrape_command.register_resume(app)


def _version_callback(requested: bool) -> None:
    """Print the version and exit, without loading configuration."""
    if requested:
        console.print(__version__)
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    config_file: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to a YAML configuration file.", exists=False),
    ] = None,
    override: Annotated[
        list[str] | None,
        typer.Option(
            "--set",
            "-s",
            help="Override a setting, as key.path=value. Repeatable. Highest precedence.",
        ),
    ] = None,
    log_level: Annotated[
        str | None,
        typer.Option("--log-level", help="Logging threshold, for example DEBUG or WARNING."),
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Log at DEBUG.")] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Log at ERROR only.")] = False,
    _version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show the version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Global options, applied before any command runs."""
    overrides = (*(override or ()), *resolve_overrides(log_level, verbose, quiet))
    ctx.obj = CliState(config_file=config_file, overrides=tuple(overrides))


def run() -> None:
    """Console script entry point.

    The outer boundary is a safety net for failures raised before the command
    group takes over -- argument parsing, for instance. Errors from inside a
    command are already handled by :class:`_ErrorHandlingGroup`.
    """
    with error_boundary():
        app()


__all__ = ["app", "run"]
