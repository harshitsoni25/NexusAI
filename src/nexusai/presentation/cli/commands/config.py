"""The ``config`` command group."""

from __future__ import annotations

import json

import typer
from rich.table import Table

from nexusai.presentation.cli.rendering.console import console
from nexusai.presentation.cli.state import CliState

group = typer.Typer(help="Inspect and verify configuration.", no_args_is_help=True)


def register(app: typer.Typer) -> None:
    """Attach this command group to ``app``."""
    app.add_typer(group, name="config")


@group.command("show")
def show(
    ctx: typer.Context,
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable output."),
) -> None:
    """Show the effective configuration and where each value came from.

    Answering "why is this setting what it is?" is the whole point of tracking
    origins through the merge. Without it, a four-layer precedence chain is a
    guessing game.
    """
    state: CliState = ctx.obj
    container = state.container()
    merged = container.configuration.merged

    if as_json:
        console.print_json(
            json.dumps(
                {
                    "settings": container.settings.model_dump(mode="json"),
                    "origins": dict(merged.origins),
                    "sources": list(container.configuration.source_names),
                }
            )
        )
        return

    table = Table(title="Effective configuration", show_lines=False)
    table.add_column("Setting", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    table.add_column("Source", style="dim")
    for key, value in sorted(_flatten(container.settings.model_dump(mode="json")).items()):
        table.add_row(key, _render(value), merged.origin_of(key) or "built-in default")
    console.print(table)
    console.print(
        "\n[dim]Precedence, lowest first: "
        + " -> ".join(container.configuration.source_names)
        + "[/dim]"
    )


@group.command("validate")
def validate(ctx: typer.Context) -> None:
    """Load and validate configuration without running anything.

    Useful in CI and as a pre-flight check in a scheduler: a misconfigured
    deployment should be caught in under a second rather than after a long run.
    """
    state: CliState = ctx.obj
    container = state.container()
    console.print(
        f"[green]Configuration is valid.[/green] "
        f"environment={container.settings.environment.value}"
    )


def _flatten(value: object, prefix: str = "") -> dict[str, object]:
    """Flatten a nested mapping into dotted keys."""
    if not isinstance(value, dict):
        return {prefix.rstrip("."): value}
    flattened: dict[str, object] = {}
    for key, nested in value.items():
        flattened.update(_flatten(nested, f"{prefix}{key}."))
    return flattened


def _render(value: object) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value) if value else "[dim](empty)[/dim]"
    return str(value)
