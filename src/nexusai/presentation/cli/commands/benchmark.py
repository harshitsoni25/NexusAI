"""The ``benchmark`` command: run controlled scenarios and manage baselines.

This runs the deterministic benchmark scenarios -- extraction, processing,
persistence, export, reporting and end-to-end -- at a chosen size tier, with
warm-up and repetition, and reports real measured timings. It can record a run as
a baseline and compare a later run against it, classifying the difference as an
improvement, stable, a regression or inconclusive. The command stays thin: the
measurement, baseline storage and comparison all live in the framework.

A browser scenario is intentionally absent. Benchmarking a real browser needs a
downloaded browser binary and is network-bound and non-deterministic, so it is
reported as NOT VERIFIED rather than measured with a fabricated number.
"""

from __future__ import annotations

import json as json_lib
from typing import cast

import typer

from nexusai.application.benchmark import SIZE_TIERS, BenchmarkConfig
from nexusai.composition.application import (
    benchmark_scenarios,
    build_baseline_store,
    build_benchmark_runner,
)
from nexusai.domain.observability.benchmark import compare_to_baseline
from nexusai.presentation.cli.rendering.console import console
from nexusai.presentation.cli.state import CliState

command = typer.Typer()

_SCENARIOS = {scenario.name: scenario for scenario in benchmark_scenarios()}


def register(app: typer.Typer) -> None:
    """Attach this command to ``app``."""
    app.command("benchmark")(benchmark)


def benchmark(
    ctx: typer.Context,
    scenario: str = typer.Option(
        "all", "--scenario", help=f"Scenario to run, or 'all'. One of: {', '.join(_SCENARIOS)}."
    ),
    size: str = typer.Option("small", "--size", help=f"Size tier: {', '.join(SIZE_TIERS)}."),
    iterations: int = typer.Option(5, "--iterations", help="Measured iterations per scenario."),
    warmup: int = typer.Option(2, "--warmup", help="Warm-up iterations before measuring."),
    record_baseline: bool = typer.Option(
        False, "--record-baseline", help="Store each run as the baseline for its scenario/size."
    ),
    compare: bool = typer.Option(
        False, "--compare", help="Compare each run against the stored baseline."
    ),
    threshold: float = typer.Option(
        0.10, "--threshold", help="Change ratio beyond which a difference is significant."
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run controlled benchmark scenarios and optionally manage baselines."""
    if iterations < 1:
        raise typer.BadParameter("iterations must be at least 1")
    if warmup < 0:
        raise typer.BadParameter("warmup cannot be negative")
    if size not in SIZE_TIERS:
        raise typer.BadParameter(f"unknown size tier: {size!r}")
    if scenario != "all" and scenario not in _SCENARIOS:
        raise typer.BadParameter(f"unknown scenario: {scenario!r}")

    state: CliState = ctx.obj
    baselines = build_baseline_store(state.container())
    all_scenarios = benchmark_scenarios()
    chosen = all_scenarios if scenario == "all" else (_SCENARIOS[scenario],)
    config = BenchmarkConfig(size=SIZE_TIERS[size], iterations=iterations, warmup=warmup)
    runner = build_benchmark_runner()

    results: list[dict[str, object]] = []
    for item in chosen:
        result = runner.run(item, config)
        entry = result.to_dict()
        if record_baseline:
            baselines.save(result)
            entry["baseline_recorded"] = True
        if compare:
            baseline = baselines.load(item.name, config.size)
            if baseline is None:
                entry["comparison"] = {"verdict": "inconclusive", "detail": "no baseline stored"}
            else:
                entry["comparison"] = compare_to_baseline(
                    result, baseline, threshold=threshold
                ).to_dict()
        results.append(entry)

    payload = {"size": size, "iterations": iterations, "scenarios": results}
    if as_json:
        console.print_json(json_lib.dumps(payload))
        return

    _render(results, size=size)


def _render(results: list[dict[str, object]], *, size: str) -> None:
    from rich.table import Table

    table = Table(title=f"Benchmark ({size})")
    table.add_column("Scenario")
    table.add_column("Median (ms)", justify="right")
    table.add_column("Throughput (rec/s)", justify="right")
    table.add_column("CPU (s)", justify="right")
    table.add_column("Errors", justify="right")
    table.add_column("Verdict")
    for entry in results:
        throughput = entry.get("throughput_records_per_second")
        comparison = entry.get("comparison")
        verdict = comparison["verdict"] if isinstance(comparison, dict) else "-"
        table.add_row(
            str(entry["scenario"]),
            f"{cast('float', entry['median_seconds']) * 1000:.3f}",
            f"{round(throughput):d}" if isinstance(throughput, (int, float)) else "-",
            f"{cast('float', entry['cpu_seconds']):.3f}",
            str(entry["errors"]),
            str(verdict),
        )
    console.print(table)
    console.print(
        "[dim]Browser retrieval and provider network timings are NOT VERIFIED "
        "in this environment (no browser binary / live network).[/dim]"
    )
