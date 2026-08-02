"""Application-service wiring for the presentation layer.

The composition root is the one place permitted to know both the application's
ports and their concrete adapters, so the wiring that turns a container into
ready-to-use use cases -- over a SQLite metadata store and the real Phase 6
services -- lives here rather than in a command. A command receives finished use
cases and stays thin; this module is where those use cases acquire their
infrastructure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexusai.application.benchmark import BenchmarkRunner, BenchmarkScenario
    from nexusai.domain.observability.metrics import MetricDefinition
    from nexusai.infrastructure.benchmark import BaselineStore
    from nexusai.infrastructure.observability import MetricsRegistry

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from nexusai.application.analysis import SiteAnalyzer
from nexusai.application.analysis.analyzer import DocumentFetcher
from nexusai.application.checkpoint.manager import CheckpointManager
from nexusai.application.jobs.manager import JobManager
from nexusai.application.runtime.context import ExecutionContext
from nexusai.application.scheduling.scheduler import Scheduler
from nexusai.application.usecases.queries import (
    JobStatusUseCase,
    ListJobsUseCase,
    StatisticsUseCase,
)
from nexusai.application.usecases.scheduling import ScheduleUseCases
from nexusai.application.usecases.workflow_factory import ScrapeCollaborators
from nexusai.composition.container import Container
from nexusai.composition.factories import build_clock, build_id_generator
from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.domain.model.retrieval import Document
from nexusai.infrastructure.persistence import (
    SqlAlchemyJobStore,
    SqlAlchemyScheduleStore,
    create_session_factory,
    create_sqlite_engine,
    initialise_schema,
)


@dataclass(frozen=True, slots=True)
class ApplicationServices:
    """The application use cases a command may need, wired and ready."""

    jobs: JobManager
    schedules: ScheduleUseCases
    scheduler: Scheduler

    def status(self) -> JobStatusUseCase:
        """Return the job-status use case."""
        return JobStatusUseCase(self.jobs)

    def list_jobs(self) -> ListJobsUseCase:
        """Return the list-jobs use case."""
        return ListJobsUseCase(self.jobs)

    def statistics(self) -> StatisticsUseCase:
        """Return the statistics use case."""
        return StatisticsUseCase(self.jobs)


def database_path(container: Container) -> Path:
    """Return the metadata database path under the configured state directory."""
    state_dir = container.settings.paths.resolve("state")
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "nexusai.db"


def build_services(container: Container) -> ApplicationServices:
    """Build application services over a SQLite metadata store."""
    engine = create_sqlite_engine(f"sqlite:///{database_path(container)}")
    initialise_schema(engine)
    factory = create_session_factory(engine)
    clock = build_clock()
    ids = build_id_generator()
    return ApplicationServices(
        jobs=JobManager(SqlAlchemyJobStore(factory), clock=clock, ids=ids),
        schedules=ScheduleUseCases(SqlAlchemyScheduleStore(factory), clock=clock, ids=ids),
        scheduler=Scheduler(),
    )


def build_scrape_collaborators(
    container: Container,
    *,
    target: str,
    dataset_id: str,
    html: bytes | None = None,
    export_formats: tuple[str, ...] = ("csv", "json"),
    report_formats: tuple[str, ...] = ("html", "json"),
) -> ScrapeCollaborators:
    """Build scrape collaborators wired to the real downstream services.

    When ``html`` is provided the retriever serves it (offline mode); otherwise it
    fetches over HTTP. Extraction is a lightweight CSS extraction over the adapter
    schema; processing wraps the results into a dataset; persistence, export and
    reporting go through the real Phase 6 services.
    """
    from datetime import UTC, datetime

    from nexusai.application.adapters import GenericHtmlAdapter
    from nexusai.application.downstream import (
        DatasetPersistenceService,
        ExportService,
        ReportAssembler,
        ReportService,
    )
    from nexusai.domain.model.extraction import (
        ExtractedValue,
        ExtractionMethod,
        FieldProvenance,
    )
    from nexusai.domain.model.processing import (
        ProcessedField,
        ProcessedRecord,
    )
    from nexusai.domain.provenance.source import SourceReference
    from nexusai.infrastructure.export import CsvExporter, JsonExporter, NdjsonExporter
    from nexusai.infrastructure.preflight import parse_robots
    from nexusai.infrastructure.reporting import HtmlReportRenderer, JsonReportRenderer

    reports_dir = container.settings.paths.resolve("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    engine = create_sqlite_engine(f"sqlite:///{database_path(container)}")
    initialise_schema(engine)
    factory = create_session_factory(engine)
    from nexusai.infrastructure.persistence import SqlAlchemyDatasetVersionStore

    persistence = DatasetPersistenceService(SqlAlchemyDatasetVersionStore(factory))
    exporter = ExportService()
    exporter.register(CsvExporter(reports_dir))
    exporter.register(JsonExporter(reports_dir))
    exporter.register(NdjsonExporter(reports_dir))
    reporter = ReportService()
    reporter.register(HtmlReportRenderer(reports_dir))
    reporter.register(JsonReportRenderer(reports_dir))
    assembler = ReportAssembler()
    schema = dict(GenericHtmlAdapter().extraction_schema())
    provenance = FieldProvenance(method=ExtractionMethod.CSS)

    def retriever(ctx: ExecutionContext) -> list[Document]:
        import httpx

        if html is not None:
            content = html
        else:
            response = httpx.get(ctx.target, follow_redirects=True, timeout=30.0)
            content = response.content
        return [
            Document(
                url=ctx.target,
                content=content,
                status_code=200,
                provider="cli",
                retrieved_at=datetime.now(UTC),
                media_type="text/html",
            )
        ]

    def extractor(documents: Sequence[Document]) -> list[ExtractionResult]:
        from lxml import html as lxml_html

        results = []
        for document in documents:
            tree = lxml_html.fromstring(document.content or b"<html></html>")
            fields = {}
            for name, selector in schema.items():
                found = tree.cssselect(selector)
                value = found[0].text_content().strip() if found else None
                fields[name] = ExtractedValue(value=value, provenance=provenance)
            results.append(ExtractionResult(fields=fields))
        return results

    def processor(extractions: Sequence[ExtractionResult]) -> ProcessedDataset:
        source = SourceReference(uri=target, retrieved_at=datetime.now(UTC), method="http-get")
        records = [
            ProcessedRecord(
                identity=f"r{index}",
                raw=extraction,
                source=source,
                fields={
                    name: ProcessedField(
                        name=name,
                        value=extraction.value(name),
                        raw_value=extraction.value(name),
                    )
                    for name in extraction.fields
                },
            )
            for index, extraction in enumerate(extractions)
        ]
        return ProcessedDataset(records=records)

    return ScrapeCollaborators(
        preflight=lambda url: parse_robots("User-agent: *\nAllow: /", target=url),
        retriever=retriever,
        extractor=extractor,
        processor=processor,
        persist=lambda ds, did, run: persistence.persist(ds, did, run_id=run),
        export=lambda ds, fmt, dest: exporter.export(ds, fmt, dest),
        report=lambda ds, fmt, dest: reporter.render(assembler.assemble(ds), fmt, dest),
        dataset_id=dataset_id,
        export_formats=export_formats,
        report_formats=report_formats,
    )


def build_site_analyzer(fetch: DocumentFetcher) -> SiteAnalyzer:
    """Build a Site Analyzer wired to the real HTML detectors.

    The detector is an infrastructure capability; the composition root supplies it
    so the presentation command and the application analyzer never import it.
    """
    from nexusai.infrastructure.analysis import analyse_html

    return SiteAnalyzer(fetch, analyse_html)


def build_scrape_runtime(container: Container) -> tuple[JobManager, CheckpointManager]:
    """Build the job manager and checkpoint manager over the metadata store.

    Returned together because a scrape or resume needs both, wired to the same
    SQLite store, so a command can obtain its runtime in one call without
    touching infrastructure itself.
    """
    from nexusai.infrastructure.persistence import (
        SqlAlchemyCheckpointStore,
        SqlAlchemyJobStore,
    )

    engine = create_sqlite_engine(f"sqlite:///{database_path(container)}")
    initialise_schema(engine)
    factory = create_session_factory(engine)
    clock = build_clock()
    ids = build_id_generator()
    jobs = JobManager(SqlAlchemyJobStore(factory), clock=clock, ids=ids)
    checkpoints = CheckpointManager(
        SqlAlchemyCheckpointStore(factory), clock=clock, ids=ids, schema_version=1
    )
    return jobs, checkpoints


def build_metrics_from_jobs(container: Container) -> MetricsRegistry:
    """Build a metrics registry populated from the persisted job history.

    The registry is filled by replaying the recorders over the jobs already
    stored -- recording each terminal job's final state and duration -- so ``stats``
    and ``doctor`` reflect real recorded metrics derived from durable data, not a
    live collector that vanished with the process. Nothing is recomputed beyond
    reading fields the jobs already carry.
    """
    from nexusai.application.observability.recorders import record_job_finished
    from nexusai.infrastructure.observability import CATALOG, MetricsRegistry, catalog_from

    registry = MetricsRegistry(catalog_from(CATALOG))
    services = build_services(container)
    for job in services.list_jobs().execute(limit=1000):
        record_job_finished(registry, job)
    return registry


def metric_catalog() -> tuple[MetricDefinition, ...]:
    """Return the framework's documented metric catalog."""
    from nexusai.infrastructure.observability.catalog import CATALOG

    return CATALOG


def build_metrics_registry() -> MetricsRegistry:
    """Build a fresh metrics registry governed by the catalog."""
    from nexusai.infrastructure.observability import (
        CATALOG,
        MetricsRegistry,
        catalog_from,
    )

    return MetricsRegistry(catalog_from(CATALOG))


def build_benchmark_runner() -> BenchmarkRunner:
    """Build a benchmark runner wired to the real resource sampler and environment."""
    from nexusai.application.benchmark import BenchmarkRunner
    from nexusai.infrastructure.benchmark import capture_environment
    from nexusai.infrastructure.observability import ResourceSampler

    return BenchmarkRunner(sampler=ResourceSampler(), capture_environment=capture_environment)


def benchmark_scenarios() -> tuple[BenchmarkScenario, ...]:
    """Return the concrete benchmark scenarios."""
    from nexusai.composition.benchmarks import ALL_SCENARIOS

    return ALL_SCENARIOS


def build_baseline_store(container: Container) -> BaselineStore:
    """Build the benchmark baseline store under the state directory."""
    from nexusai.infrastructure.benchmark import BaselineStore

    return BaselineStore(container.settings.paths.resolve("state") / "benchmarks")
