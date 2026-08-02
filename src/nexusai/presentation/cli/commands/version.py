"""The ``version`` command."""

from __future__ import annotations

import platform
import sys

import typer
from rich.table import Table

from nexusai.__about__ import __version__
from nexusai.presentation.cli.rendering.console import console

command = typer.Typer()


def register(app: typer.Typer) -> None:
    """Attach this command to ``app``."""
    app.command("version")(version)


def version(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Include interpreter and platform detail."
    ),
) -> None:
    """Show the installed Nexus AI version."""
    if not verbose:
        console.print(__version__)
        return
    table = Table(show_header=False, box=None)
    table.add_row("Nexus AI", __version__)
    table.add_row("Python", sys.version.split()[0])
    table.add_row("Platform", platform.platform())
    console.print(table)
