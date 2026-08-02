"""The ``validate``, ``export`` and ``report`` commands.

Each builds a dataset from a local HTML file through the real extraction and
processing path, then applies its one operation: ``validate`` reports the Phase 5
validation summary, ``export`` writes the dataset in the requested Phase 6 format,
and ``report`` renders a Phase 6 report. Building from a file keeps each command
self-contained and deterministic, and none of them reimplements the capability it
invokes.
"""

from __future__ import annotations

import json as json_lib
from pathlib import Path

import typer

from nexusai.application.usecases.workflow_factory import ScrapeCollaborators
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.presentation.cli.exit_codes import ExitCode
from nexusai.presentation.cli.rendering.console import console
from nexusai.presentation.cli.state import CliState
from nexusai.presentation.cli.support import build_scrape_collaborators

command = typer.Typer()


def register(app: typer.Typer) -> None:
    """Attach the dataset commands to ``app``."""
    app.command("validate")(validate)
    app.command("export")(export)
    app.command("report")(report)


class _MiniContext:
    """A minimal stand-in exposing only the ``target`` a retriever reads."""

    def __init__(self, target: str) -> None:
        self.target = target


def _prepare(
    ctx: typer.Context, target: str, from_file: Path
) -> tuple[ScrapeCollaborators, ProcessedDataset]:
    """Build collaborators over the file bytes and produce the dataset."""
    state: CliState = ctx.obj
    collaborators = build_scrape_collaborators(
        state.container(),
        target=target,
        dataset_id="adhoc",
        html=from_file.read_bytes(),
    )
    documents = collaborators.retriever(_MiniContext(target))  # type: ignore[arg-type]
    dataset = collaborators.processor(collaborators.extractor(documents))
    return collaborators, dataset


def validate(
    ctx: typer.Context,
    target: str = typer.Argument(..., help="A label for the dataset source."),
    from_file: Path = typer.Option(..., "--from-file", help="HTML file to validate."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Validate a dataset built from a local HTML file."""
    _, dataset = _prepare(ctx, target, from_file)
    summary = {"records": len(dataset), "valid": dataset.is_valid}
    if as_json:
        console.print_json(json_lib.dumps(summary))
    else:
        console.print(
            f"Records: {summary['records']} — " f"{'valid' if summary['valid'] else 'INVALID'}"
        )
    if not dataset.is_valid:
        raise typer.Exit(code=int(ExitCode.VALIDATION_FAILURE))


def export(
    ctx: typer.Context,
    target: str = typer.Argument(..., help="A label for the dataset source."),
    from_file: Path = typer.Option(..., "--from-file", help="HTML file to export."),
    export_format: str = typer.Option("csv", "--format", help="Export format."),
) -> None:
    """Export a dataset built from a local HTML file."""
    collaborators, dataset = _prepare(ctx, target, from_file)
    manifest = collaborators.export(dataset, export_format, f"export.{export_format}")
    console.print(f"Exported to [cyan]{manifest.artifact.locator}[/cyan]")


def report(
    ctx: typer.Context,
    target: str = typer.Argument(..., help="A label for the dataset source."),
    from_file: Path = typer.Option(..., "--from-file", help="HTML file to report on."),
    report_format: str = typer.Option("html", "--format", help="Report format."),
) -> None:
    """Render a report for a dataset built from a local HTML file."""
    collaborators, dataset = _prepare(ctx, target, from_file)
    manifest = collaborators.report(dataset, report_format, f"report.{report_format}")
    console.print(f"Report written: [cyan]{manifest.artifact.locator}[/cyan]")
