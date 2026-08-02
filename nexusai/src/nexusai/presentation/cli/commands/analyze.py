"""The ``analyze-site`` command.

Analysis needs content to inspect. To keep the command testable and safe, it can
read a local HTML file (``--from-file``) as well as fetch a URL. URL schemes are
validated -- only http and https are permitted -- so the command cannot be pointed
at a ``file://`` or other unsafe scheme.
"""

from __future__ import annotations

import json as json_lib
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.table import Table

from nexusai.application.analysis import StrategyRecommender
from nexusai.application.usecases.analysis import AnalyzeSiteUseCase
from nexusai.composition.application import build_site_analyzer
from nexusai.domain.model.analysis import RetrievalStrategy
from nexusai.domain.model.retrieval import Document
from nexusai.presentation.cli.exit_codes import ExitCode
from nexusai.presentation.cli.rendering.console import console

command = typer.Typer()


def register(app: typer.Typer) -> None:
    """Attach this command to ``app``."""
    app.command("analyze-site")(analyze_site)


def analyze_site(
    ctx: typer.Context,
    target: str = typer.Argument(..., help="The URL to analyse."),
    from_file: Path | None = typer.Option(
        None, "--from-file", help="Analyse a local HTML file instead of fetching."
    ),
    strategy: str | None = typer.Option(
        None, "--strategy", help="Override the recommended strategy."
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Analyse a target's observable characteristics and recommend a strategy."""
    _ = ctx
    if from_file is None and not target.startswith(("http://", "https://")):
        raise typer.BadParameter("target must be an http or https URL")
    override = _parse_strategy(strategy)

    fetch: Callable[[str], Document]
    if from_file is not None:
        content = from_file.read_bytes()

        def fetch(_url: str) -> Document:
            return Document(
                url=target,
                content=content,
                status_code=200,
                provider="file",
                retrieved_at=datetime.now(UTC),
                media_type="text/html",
            )

    else:
        fetch = _http_fetcher()

    use_case = AnalyzeSiteUseCase(build_site_analyzer(fetch), StrategyRecommender())
    result = use_case.execute(target, override=override)

    if as_json:
        console.print_json(json_lib.dumps(result.to_dict()))
        return
    _render(result)


def _parse_strategy(strategy: str | None) -> RetrievalStrategy | None:
    if strategy is None:
        return None
    try:
        return RetrievalStrategy(strategy)
    except ValueError as error:
        raise typer.BadParameter("strategy must be http, browser, api or hybrid") from error


def _http_fetcher() -> Callable[[str], Document]:
    import httpx

    def fetch(url: str) -> Document:
        response = httpx.get(url, follow_redirects=True, timeout=30.0)
        return Document(
            url=str(response.url),
            content=response.content,
            status_code=response.status_code,
            provider="httpx",
            retrieved_at=datetime.now(UTC),
            media_type=response.headers.get("content-type", "text/html").split(";")[0],
        )

    return fetch


def _render(result: object) -> None:
    analysis = result.analysis  # type: ignore[attr-defined]
    recommendation = result.recommendation  # type: ignore[attr-defined]
    table = Table(title=f"Analysis of {analysis.target}")
    table.add_column("Characteristic", style="cyan")
    table.add_column("Confidence")
    table.add_column("Evidence")
    for observation in analysis.observations:
        table.add_row(
            observation.characteristic.value,
            observation.confidence.value,
            observation.evidence,
        )
    console.print(table)
    console.print(
        f"Recommended strategy: [green]{recommendation.strategy.value}[/green] "
        f"({recommendation.confidence.value}) — {recommendation.rationale}"
    )
    if recommendation.alternatives:
        console.print("Alternatives: " + ", ".join(s.value for s in recommendation.alternatives))
    _ = ExitCode.SUCCESS
