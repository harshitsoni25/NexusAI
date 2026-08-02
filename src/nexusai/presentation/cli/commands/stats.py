"""The ``stats`` command: job roll-ups, the metric catalog, and health.

Beyond the job-outcome counts, this exposes the two observability surfaces an
operator needs from the command line: the documented metric catalog (so every
metric the framework records is discoverable, with its type, unit and meaning),
and an operational health summary derived from the persisted job history. The
health summary reads real recorded metrics -- replayed from durable job data -- so
it reflects what happened, not a live collector that vanished with the process.
"""

from __future__ import annotations

import json as json_lib

import typer
from rich.table import Table

from nexusai.application.observability import assess_health
from nexusai.composition.application import build_metrics_from_jobs, metric_catalog
from nexusai.presentation.cli.rendering.console import console
from nexusai.presentation.cli.state import CliState
from nexusai.presentation.cli.support import build_services

command = typer.Typer()

_HEALTH_STYLE = {"pass": "green", "warning": "yellow", "fail": "red"}


def register(app: typer.Typer) -> None:
    """Attach this command to ``app``."""
    app.command("stats")(stats)


def stats(
    ctx: typer.Context,
    catalog: bool = typer.Option(
        False, "--catalog", help="Show the documented metric catalog instead of job stats."
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Show job statistics, operational health, or the metric catalog."""
    state: CliState = ctx.obj
    container = state.container()

    if catalog:
        entries = [definition.to_dict() for definition in metric_catalog()]
        if as_json:
            console.print_json(json_lib.dumps({"metrics": entries}))
            return
        _render_catalog(entries)
        return

    statistics = build_services(container).statistics().execute()
    registry = build_metrics_from_jobs(container)
    health = assess_health(registry)

    if as_json:
        console.print_json(
            json_lib.dumps(
                {
                    "jobs": statistics.to_dict(),
                    "health": health.to_dict(),
                    "metrics": registry.snapshot(),
                }
            )
        )
        return

    table = Table(title="Job statistics")
    table.add_column("State", style="cyan")
    table.add_column("Count", justify="right")
    for job_state, count in sorted(statistics.by_state.items()):
        table.add_row(job_state, str(count))
    table.add_row("[bold]total[/bold]", f"[bold]{statistics.total_jobs}[/bold]")
    console.print(table)

    health_table = Table(title=f"Operational health: {health.status.value.upper()}")
    health_table.add_column("Signal", style="cyan")
    health_table.add_column("Status")
    health_table.add_column("Detail")
    for check in health.checks:
        style = _HEALTH_STYLE.get(check.status.value, "white")
        health_table.add_row(
            check.name, f"[{style}]{check.status.value.upper()}[/{style}]", check.detail
        )
    console.print(health_table)


def _render_catalog(entries: list[dict[str, object]]) -> None:
    table = Table(title="Metric catalog")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type")
    table.add_column("Unit")
    table.add_column("Dimensions")
    table.add_column("Description")
    for entry in entries:
        dimensions = ", ".join(entry["dimensions"]) if entry["dimensions"] else "-"  # type: ignore[arg-type]
        table.add_row(
            str(entry["name"]),
            str(entry["type"]),
            str(entry["unit"]),
            dimensions,
            str(entry["description"]),
        )
    console.print(table)
