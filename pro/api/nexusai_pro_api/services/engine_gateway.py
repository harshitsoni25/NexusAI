"""The one module that imports the Nexus AI engine.

Every engine capability the API exposes is reached through this gateway, so the
coupling to ``nexusai`` lives in a single place and the rest of the backend
depends only on the gateway. The engine is treated as an immutable library: the
gateway calls its composition-root build functions and use-cases exactly as the CLI
does, and adds no scraping logic of its own.

The engine is synchronous (ADR-0020); nothing here is awaited. Long-running work is
handed to the job runner, which executes these synchronous calls off the event loop.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# The engine — imported only here.
from nexusai.application.usecases.queries import (
    ListJobsUseCase,
    StatisticsUseCase,
)
from nexusai.application.usecases.scrape import ResumeJobUseCase, StartScrapeUseCase
from nexusai.composition.application import (
    build_scrape_collaborators,
    build_scrape_runtime,
)
from nexusai.composition.container import Container, bootstrap
from nexusai.domain.model.job import Job


class EngineGateway:
    """A thin façade over the certified engine's composition root and use-cases."""

    def __init__(self, container: Container) -> None:
        self._container = container

    # --- lifecycle ---------------------------------------------------------

    @classmethod
    def create(cls, *, config_file: Path | None = None) -> EngineGateway:
        """Bootstrap the engine once and wrap the resulting container."""
        container = bootstrap(config_file=config_file)
        return cls(container)

    @property
    def container(self) -> Container:
        return self._container

    # --- scraping (synchronous; invoked from the job runner) ---------------

    def run_scrape(
        self,
        target: str,
        *,
        dataset_id: str,
        export_formats: tuple[str, ...],
        report_formats: tuple[str, ...],
    ) -> Job:
        """Execute a full scrape workflow and return the final job."""
        jobs, checkpoints = build_scrape_runtime(self._container)
        collaborators = build_scrape_collaborators(
            self._container,
            target=target,
            dataset_id=dataset_id,
            export_formats=export_formats,
            report_formats=report_formats,
        )
        use_case = StartScrapeUseCase(
            jobs=jobs,
            checkpoints=checkpoints,
            ids=self._container.id_generator,
            logger=self._container.logger,
        )
        outcome = use_case.execute(
            target,
            collaborators,
            correlation_id=str(self._container.correlation_id),
        )
        return outcome.job

    def resume_scrape(
        self,
        job_id: str,
        *,
        target: str,
        dataset_id: str,
        export_formats: tuple[str, ...],
        report_formats: tuple[str, ...],
    ) -> Job:
        """Resume a previously started job from its checkpoint."""
        jobs, checkpoints = build_scrape_runtime(self._container)
        collaborators = build_scrape_collaborators(
            self._container,
            target=target,
            dataset_id=dataset_id,
            export_formats=export_formats,
            report_formats=report_formats,
        )
        use_case = ResumeJobUseCase(
            jobs=jobs,
            checkpoints=checkpoints,
            logger=self._container.logger,
        )
        outcome = use_case.execute(
            job_id,
            collaborators,
            correlation_id=str(self._container.correlation_id),
        )
        return outcome.job

    # --- read side ---------------------------------------------------------

    def get_job(self, job_id: str) -> Job | None:
        jobs, _ = build_scrape_runtime(self._container)
        return jobs.get(job_id)

    def list_jobs(self, *, limit: int = 50) -> list[Job]:
        jobs, _ = build_scrape_runtime(self._container)
        return ListJobsUseCase(jobs).execute(limit=limit)

    def statistics(self) -> Any:
        jobs, _ = build_scrape_runtime(self._container)
        return StatisticsUseCase(jobs).execute()

    # --- plugins -----------------------------------------------------------

    def plugin_report(self) -> Any:
        """Return the engine's plugin load report (loaded, failed, contracts)."""
        return self._container.plugin_report

    def plugin_registry(self) -> Any:
        return self._container.plugins

    # --- health ------------------------------------------------------------

    def doctor(self) -> Any:
        """Run the engine's readiness checks via the Doctor use case.

        Constructed exactly as the CLI's ``doctor`` command does, so the API reports
        the same readiness view without duplicating any check logic.
        """
        from nexusai.application.usecases.doctor import DoctorUseCase

        return DoctorUseCase(
            adapter_names=("generic-html",),
            plugin_count=len(self._container.plugins),
        ).execute()
