"""The ``doctor`` command: environment readiness."""

from __future__ import annotations

import json as json_lib

import typer
from rich.table import Table

from nexusai.application.observability import assess_health
from nexusai.application.usecases.doctor import CheckStatus, DoctorUseCase
from nexusai.composition.application import build_metrics_from_jobs
from nexusai.presentation.cli.exit_codes import ExitCode
from nexusai.presentation.cli.rendering.console import console
from nexusai.presentation.cli.state import CliState

command = typer.Typer()

_STATUS_STYLE = {
    CheckStatus.PASS: "green",
    CheckStatus.WARNING: "yellow",
    CheckStatus.FAIL: "red",
}


def register(app: typer.Typer) -> None:
    """Attach this command to ``app``."""
    app.command("doctor")(doctor)


def doctor(
    ctx: typer.Context,
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Check whether the environment is ready to run scrapes."""
    state: CliState = ctx.obj
    container = state.container()
    report = DoctorUseCase(
        adapter_names=("generic-html",),
        plugin_count=len(container.plugins),
    ).execute()
    health = assess_health(build_metrics_from_jobs(container))

    if as_json:
        payload = report.to_dict()
        payload["operational_health"] = health.to_dict()
        console.print_json(json_lib.dumps(payload))
    else:
        table = Table(title="Nexus AI doctor")
        table.add_column("Check", style="cyan", no_wrap=True)
        table.add_column("Status")
        table.add_column("Detail")
        for check in report.checks:
            style = _STATUS_STYLE[check.status]
            table.add_row(
                check.name,
                f"[{style}]{check.status.value.upper()}[/{style}]",
                check.detail + (f" — {check.remediation}" if check.remediation else ""),
            )
        console.print(table)
        console.print(
            f"Operational health (from job history): " f"[bold]{health.status.value.upper()}[/bold]"
        )

    if not report.ok:
        raise typer.Exit(code=int(ExitCode.DEPENDENCY_FAILURE))
