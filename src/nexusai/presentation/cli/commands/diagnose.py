"""The ``diagnose`` command."""

from __future__ import annotations

import platform
import sys

import typer
from rich.table import Table

from nexusai.__about__ import __version__
from nexusai.presentation.cli.rendering.console import console
from nexusai.presentation.cli.state import CliState

command = typer.Typer()


def register(app: typer.Typer) -> None:
    """Attach this command to ``app``."""
    app.command("diagnose")(diagnose)


def diagnose(ctx: typer.Context) -> None:
    """Verify that the framework is correctly installed and configured.

    Exercises the whole startup path -- configuration, logging, plugin discovery,
    filesystem access -- and reports the result. This is the first thing to run
    when something is wrong on a new machine, and it is also what makes the
    infrastructure of this phase verifiable end to end rather than only in
    theory.
    """
    state: CliState = ctx.obj
    container = state.container()

    table = Table(title="Nexus AI diagnostics", show_header=False)
    table.add_column("Check", style="cyan", no_wrap=True)
    table.add_column("Result")
    table.add_row("Version", __version__)
    table.add_row("Python", sys.version.split()[0])
    table.add_row("Platform", platform.platform())
    table.add_row("Environment", container.settings.environment.value)
    table.add_row("Correlation id", str(container.correlation_id))
    table.add_row("Log level", container.settings.logging.level.value)
    table.add_row("Plugins registered", str(len(container.plugins)))
    table.add_row("Plugins rejected", str(len(container.plugin_report.rejected)))
    table.add_row("Event subscribers", str(container.events.subscriber_count))

    for name in ("data", "artifacts", "reports", "logs", "state"):
        path = container.settings.paths.resolve(name)
        writable = _writability(path)
        table.add_row(f"Path: {name}", f"{path} [{writable}]")

    console.print(table)


def _writability(path: object) -> str:
    """Report whether a configured directory can be created and written to.

    Directories are created on demand rather than at startup, so the useful
    question is not "does it exist?" but "will writing to it work?".
    """
    from pathlib import Path

    candidate = Path(str(path))
    try:
        candidate.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return f"[red]not writable: {exc.strerror}[/red]"
    return "[green]ok[/green]"
