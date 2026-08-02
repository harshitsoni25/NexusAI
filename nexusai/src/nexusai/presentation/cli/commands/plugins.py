"""The ``plugins`` command group."""

from __future__ import annotations

import typer
from rich.table import Table

from nexusai.application.contracts import describe_extension_points
from nexusai.presentation.cli.rendering.console import console
from nexusai.presentation.cli.state import CliState

group = typer.Typer(help="Inspect the plugin ecosystem.", no_args_is_help=True)


def register(app: typer.Typer) -> None:
    """Attach this command group to ``app``."""
    app.add_typer(group, name="plugins")


@group.command("list")
def list_plugins(ctx: typer.Context) -> None:
    """List every plugin that was discovered, and every one that was rejected.

    Rejections are shown alongside acceptances rather than hidden in a log,
    because a plugin that silently failed to load looks identical to a plugin
    that was never installed.
    """
    state: CliState = ctx.obj
    container = state.container()
    registered = container.plugins.describe()

    if registered:
        table = Table(title=f"Registered plugins ({len(registered)})")
        table.add_column("Extension point", style="cyan")
        table.add_column("Name", style="bold")
        table.add_column("Version")
        table.add_column("API", style="dim")
        table.add_column("Description", style="dim")
        for metadata in registered:
            table.add_row(
                metadata.extension_point.value,
                metadata.name,
                metadata.version,
                str(metadata.api_version),
                metadata.description or "-",
            )
        console.print(table)
    else:
        console.print("[dim]No plugins are registered.[/dim]")

    rejected = container.plugin_report.rejected
    if rejected:
        table = Table(title=f"Rejected ({len(rejected)})", border_style="yellow")
        table.add_column("Reference", style="yellow")
        table.add_column("Reason")
        for item in rejected:
            table.add_row(item.reference, item.reason)
        console.print(table)


@group.command("contracts")
def contracts() -> None:
    """Show the extension points and the contract version each one provides.

    Plugin authors need this to know what to declare. Versions advance per
    extension point, independently of the framework release version.
    """
    table = Table(title="Extension points")
    table.add_column("Extension point", style="cyan")
    table.add_column("Supported API version")
    for description in describe_extension_points():
        table.add_row(description.name, str(description.supported_api_version))
    console.print(table)
