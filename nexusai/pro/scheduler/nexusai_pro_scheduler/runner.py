"""Turning a due schedule into an actual scrape.

The executor depends on a small ``ScrapeRunner`` protocol so it can be tested with a
fake. The real implementation, ``EngineScrapeRunner``, reuses the certified engine
exactly as the CLI and the FastAPI backend do — bootstrapping a container once and
driving ``StartScrapeUseCase`` through the composition root. The engine is never
modified; it is imported as a library.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .models import ScrapeSpec


@dataclass(slots=True)
class RunResult:
    job_id: str
    state: str


class ScrapeRunner(Protocol):
    def run(self, spec: ScrapeSpec) -> RunResult: ...


class EngineScrapeRunner:
    """Runs a scrape by reusing the frozen Nexus AI engine composition root."""

    def __init__(self, *, config_file: Path | None = None) -> None:
        # Imported lazily so tests that use a fake runner need no engine present.
        from nexusai.composition.container import bootstrap

        self._container = bootstrap(config_file=config_file)

    def run(self, spec: ScrapeSpec) -> RunResult:
        from nexusai.application.usecases.scrape import StartScrapeUseCase
        from nexusai.composition.application import (
            build_scrape_collaborators,
            build_scrape_runtime,
        )

        dataset_id = spec.dataset_id or f"sched-{abs(hash(spec.target)) % 10_000_000:07d}"
        jobs, checkpoints = build_scrape_runtime(self._container)
        collaborators = build_scrape_collaborators(
            self._container,
            target=spec.target,
            dataset_id=dataset_id,
            export_formats=spec.export_formats,
            report_formats=spec.report_formats,
        )
        use_case = StartScrapeUseCase(
            jobs=jobs,
            checkpoints=checkpoints,
            ids=self._container.id_generator,
            logger=self._container.logger,
        )
        outcome = use_case.execute(
            spec.target,
            collaborators,
            correlation_id=str(self._container.correlation_id),
        )
        job = outcome.job
        state = getattr(getattr(job, "state", None), "value", "completed")
        return RunResult(job_id=job.job_id, state=str(state))
