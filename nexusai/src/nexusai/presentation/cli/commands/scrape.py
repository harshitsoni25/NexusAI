"""The ``scrape`` and ``resume`` commands."""

from __future__ import annotations

import json as json_lib
from pathlib import Path

import typer

from nexusai.application.usecases.scrape import ResumeJobUseCase, StartScrapeUseCase
from nexusai.composition.application import (
    build_scrape_collaborators,
    build_scrape_runtime,
)
from nexusai.domain.model.job import JobState
from nexusai.presentation.cli.exit_codes import ExitCode
from nexusai.presentation.cli.rendering.console import console
from nexusai.presentation.cli.state import CliState

command = typer.Typer()

_FINAL_EXIT = {
    JobState.COMPLETED: ExitCode.SUCCESS,
    JobState.PARTIAL: ExitCode.PARTIAL,
    JobState.FAILED: ExitCode.EXECUTION_FAILURE,
    JobState.CANCELLED: ExitCode.EXECUTION_FAILURE,
}


def register(app: typer.Typer) -> None:
    """Attach the ``scrape`` command to ``app``."""
    app.command("scrape")(scrape)


def scrape(
    ctx: typer.Context,
    target: str = typer.Argument(..., help="The site or URL to scrape."),
    dataset_id: str = typer.Option("default", "--dataset-id", help="Logical dataset id."),
    from_file: Path | None = typer.Option(
        None, "--from-file", help="Scrape a local HTML file instead of fetching."
    ),
    export_format: list[str] | None = typer.Option(
        None, "--export", help="Export format(s). Repeatable."
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run a complete scraping workflow for a target."""
    if from_file is None and not target.startswith(("http://", "https://")):
        raise typer.BadParameter("target must be an http or https URL")
    if not dataset_id.replace("-", "").replace("_", "").isalnum():
        raise typer.BadParameter("dataset-id must be alphanumeric")
    formats = tuple(export_format) if export_format else ("csv", "json")

    state: CliState = ctx.obj
    container = state.container()
    jobs, checkpoints = build_scrape_runtime(container)
    collaborators = build_scrape_collaborators(
        container,
        target=target,
        dataset_id=dataset_id,
        html=from_file.read_bytes() if from_file else None,
        export_formats=formats,
    )
    use_case = StartScrapeUseCase(
        jobs=jobs,
        checkpoints=checkpoints,
        ids=container.id_generator,
        logger=container.logger,
    )
    outcome = use_case.execute(target, collaborators, correlation_id=str(container.correlation_id))

    if as_json:
        console.print_json(json_lib.dumps(outcome.job.to_dict()))
    else:
        console.print(
            f"Job [cyan]{outcome.job.job_id}[/cyan] finished: "
            f"[bold]{outcome.job.state.value}[/bold] "
            f"(dataset {outcome.job.dataset_ref} v{outcome.job.dataset_version})"
        )
    raise typer.Exit(code=int(_FINAL_EXIT.get(outcome.job.state, ExitCode.FAILURE)))


def register_resume(app: typer.Typer) -> None:
    """Attach the ``resume`` command to ``app``."""
    app.command("resume")(resume)


def resume(
    ctx: typer.Context,
    job_id: str = typer.Argument(..., help="The job to resume."),
    from_file: Path | None = typer.Option(
        None, "--from-file", help="Resume against a local HTML file."
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Resume a paused job from its latest valid checkpoint."""
    state: CliState = ctx.obj
    container = state.container()
    jobs, checkpoints = build_scrape_runtime(container)
    job = jobs.require(job_id)
    collaborators = build_scrape_collaborators(
        container,
        target=job.target,
        dataset_id=job.dataset_ref or "default",
        html=from_file.read_bytes() if from_file else None,
    )
    use_case = ResumeJobUseCase(jobs=jobs, checkpoints=checkpoints, logger=container.logger)
    outcome = use_case.execute(job_id, collaborators, correlation_id=str(container.correlation_id))
    if as_json:
        console.print_json(json_lib.dumps(outcome.job.to_dict()))
    else:
        console.print(f"Resumed [cyan]{job_id}[/cyan]: {outcome.job.state.value}")
    raise typer.Exit(code=int(_FINAL_EXIT.get(outcome.job.state, ExitCode.FAILURE)))
