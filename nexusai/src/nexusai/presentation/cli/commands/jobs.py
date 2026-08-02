"""The ``jobs`` and ``status`` commands."""

from __future__ import annotations

import json as json_lib

import typer
from rich.table import Table

from nexusai.presentation.cli.rendering.console import console
from nexusai.presentation.cli.state import CliState
from nexusai.presentation.cli.support import build_services

command = typer.Typer()


def register(app: typer.Typer) -> None:
    """Attach the ``jobs`` and ``status`` commands to ``app``."""
    app.command("jobs")(jobs)
    app.command("status")(status)


def jobs(
    ctx: typer.Context,
    limit: int = typer.Option(20, "--limit", help="How many recent jobs to show."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """List recent jobs, newest first."""
    if limit < 1:
        raise typer.BadParameter("limit must be at least 1")
    state: CliState = ctx.obj
    services = build_services(state.container())
    recent = services.list_jobs().execute(limit=limit)

    if as_json:
        console.print_json(json_lib.dumps([job.to_dict() for job in recent]))
        return
    table = Table(title="Recent jobs")
    table.add_column("Job", style="cyan", no_wrap=True)
    table.add_column("Target")
    table.add_column("State")
    table.add_column("Stage")
    for job in recent:
        table.add_row(job.job_id, job.target, job.state.value, job.current_stage or "-")
    console.print(table)


def status(
    ctx: typer.Context,
    job_id: str = typer.Argument(..., help="The job to inspect."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Show the status of one job."""
    state: CliState = ctx.obj
    services = build_services(state.container())
    job_status = services.status().execute(job_id)

    if as_json:
        console.print_json(json_lib.dumps(job_status.to_dict()))
        return
    table = Table(show_header=False, title=f"Job {job_id}")
    for key, value in job_status.to_dict().items():
        table.add_row(str(key), str(value))
    console.print(table)
