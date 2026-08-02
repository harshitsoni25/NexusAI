"""The ``schedule`` command group: create, list, enable, disable, delete."""

from __future__ import annotations

import json as json_lib

import typer
from rich.table import Table

from nexusai.application.usecases.scheduling import ScheduleUseCases
from nexusai.domain.model.schedule import (
    OverlapPolicy,
    ScheduleExpression,
    ScheduleKind,
)
from nexusai.presentation.cli.exit_codes import ExitCode
from nexusai.presentation.cli.rendering.console import console
from nexusai.presentation.cli.state import CliState
from nexusai.presentation.cli.support import build_services

command = typer.Typer(help="Manage recurring schedules.")


def register(app: typer.Typer) -> None:
    """Attach the schedule command group to ``app``."""
    app.add_typer(command, name="schedule")


def _uses(ctx: typer.Context) -> ScheduleUseCases:
    state: CliState = ctx.obj
    return build_services(state.container()).schedules


@command.command("create")
def create(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", help="A name for the schedule."),
    target: str = typer.Option(..., "--target", help="The site or URL to scrape."),
    interval: int = typer.Option(..., "--interval-seconds", help="Seconds between runs."),
    overlap: str = typer.Option("skip", "--overlap", help="Overlap policy: allow, skip or queue."),
) -> None:
    """Create an interval schedule."""
    if interval < 1:
        raise typer.BadParameter("interval-seconds must be at least 1")
    if not target.startswith(("http://", "https://")):
        raise typer.BadParameter("target must be an http or https URL")
    try:
        policy = OverlapPolicy(overlap)
    except ValueError as error:
        raise typer.BadParameter("overlap must be allow, skip or queue") from error

    schedule = _uses(ctx).create(
        name=name,
        target=target,
        expression=ScheduleExpression(kind=ScheduleKind.INTERVAL, interval_seconds=float(interval)),
        overlap_policy=policy,
    )
    console.print(f"Created schedule [cyan]{schedule.schedule_id}[/cyan] ({schedule.name})")


@command.command("list")
def list_schedules(
    ctx: typer.Context,
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """List all schedules."""
    schedules = _uses(ctx).list()
    if as_json:
        console.print_json(json_lib.dumps([s.to_dict() for s in schedules]))
        return
    table = Table(title="Schedules")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Target")
    table.add_column("Enabled")
    table.add_column("Next run")
    for schedule in schedules:
        table.add_row(
            schedule.schedule_id,
            schedule.name,
            schedule.target,
            "yes" if schedule.enabled else "no",
            schedule.next_run.isoformat() if schedule.next_run else "-",
        )
    console.print(table)


@command.command("enable")
def enable(ctx: typer.Context, schedule_id: str = typer.Argument(...)) -> None:
    """Enable a schedule."""
    _uses(ctx).set_enabled(schedule_id, enabled=True)
    console.print(f"Enabled [cyan]{schedule_id}[/cyan]")


@command.command("disable")
def disable(ctx: typer.Context, schedule_id: str = typer.Argument(...)) -> None:
    """Disable a schedule."""
    _uses(ctx).set_enabled(schedule_id, enabled=False)
    console.print(f"Disabled [cyan]{schedule_id}[/cyan]")


@command.command("delete")
def delete(ctx: typer.Context, schedule_id: str = typer.Argument(...)) -> None:
    """Delete a schedule."""
    _uses(ctx).delete(schedule_id)
    console.print(f"Deleted [cyan]{schedule_id}[/cyan]")
    raise typer.Exit(code=int(ExitCode.SUCCESS))
