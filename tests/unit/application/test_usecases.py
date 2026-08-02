"""Tests for application use cases, including a controlled end-to-end scrape."""

from __future__ import annotations

from pathlib import Path

import pytest

from application_builders import make_dataset, make_document, make_extraction
from nexusai.application.analysis import SiteAnalyzer, StrategyRecommender
from nexusai.application.checkpoint.manager import CheckpointManager
from nexusai.application.downstream import (
    DatasetPersistenceService,
    ExportService,
    ReportAssembler,
    ReportService,
)
from nexusai.application.jobs.manager import JobManager
from nexusai.application.usecases.analysis import AnalyzeSiteUseCase
from nexusai.application.usecases.doctor import CheckStatus, DoctorUseCase
from nexusai.application.usecases.queries import (
    JobStatusUseCase,
    ListJobsUseCase,
    StatisticsUseCase,
)
from nexusai.application.usecases.scrape import StartScrapeUseCase
from nexusai.application.usecases.workflow_factory import ScrapeCollaborators
from nexusai.domain.model.analysis import RetrievalStrategy
from nexusai.domain.model.job import JobState
from nexusai.infrastructure.analysis import analyse_html
from nexusai.infrastructure.export import CsvExporter, JsonExporter
from nexusai.infrastructure.persistence import (
    SqlAlchemyCheckpointStore,
    SqlAlchemyDatasetVersionStore,
    SqlAlchemyJobStore,
    create_session_factory,
    create_sqlite_engine,
    initialise_schema,
)
from nexusai.infrastructure.preflight import parse_robots
from nexusai.infrastructure.reporting import HtmlReportRenderer, JsonReportRenderer
from nexusai.testing import FrozenClock, RecordingLogger, SequentialIdGenerator

_HTML = b"<html><body>" + b"content " * 40 + b"</body></html>"


@pytest.fixture
def factory():  # type: ignore[no-untyped-def]
    engine = create_sqlite_engine()
    initialise_schema(engine)
    return create_session_factory(engine)


class TestQueryUseCases:
    def test_status_of_a_job(self, factory) -> None:  # type: ignore[no-untyped-def]
        manager = JobManager(
            SqlAlchemyJobStore(factory), clock=FrozenClock(), ids=SequentialIdGenerator()
        )
        job = manager.transition(manager.create("https://x"), JobState.RUNNING)
        manager.update_stage(job, "retrieve")
        status = JobStatusUseCase(manager).execute(job.job_id)
        assert status.state == "running"
        assert status.total_stages > 0

    def test_list_and_statistics(self, factory) -> None:  # type: ignore[no-untyped-def]
        manager = JobManager(
            SqlAlchemyJobStore(factory), clock=FrozenClock(), ids=SequentialIdGenerator()
        )
        manager.create("https://a")
        manager.create("https://b")
        assert len(ListJobsUseCase(manager).execute()) == 2
        stats = StatisticsUseCase(manager).execute()
        assert stats.total_jobs == 2
        assert stats.by_state["created"] == 2


class TestAnalyzeUseCase:
    def test_analyse_and_recommend(self) -> None:
        analyzer = SiteAnalyzer(lambda t: make_document(body=_HTML), analyse_html)
        result = AnalyzeSiteUseCase(analyzer, StrategyRecommender()).execute("https://x")
        assert result.analysis.target == "https://x"
        assert result.recommendation.strategy is RetrievalStrategy.HTTP

    def test_override_is_reflected(self) -> None:
        analyzer = SiteAnalyzer(lambda t: make_document(body=_HTML), analyse_html)
        result = AnalyzeSiteUseCase(analyzer, StrategyRecommender()).execute(
            "https://x", override=RetrievalStrategy.BROWSER
        )
        assert result.recommendation.strategy is RetrievalStrategy.BROWSER
        assert result.recommendation.overridden


class TestDoctorUseCase:
    def test_reports_python_pass_and_required_dependency(self) -> None:
        report = DoctorUseCase(adapter_names=("generic-html",), plugin_count=1).execute()
        assert report.ok
        names = {c.name: c.status for c in report.checks}
        assert names["python-version"] is CheckStatus.PASS
        assert names["required:sqlalchemy"] is CheckStatus.PASS


class TestControlledEndToEnd:
    def test_scrape_persists_exports_and_reports(self, factory, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
        out = tmp_path / "out"
        out.mkdir()
        persistence = DatasetPersistenceService(SqlAlchemyDatasetVersionStore(factory))
        exporter = ExportService()
        exporter.register(CsvExporter(out))
        exporter.register(JsonExporter(out))
        reporter = ReportService()
        reporter.register(HtmlReportRenderer(out))
        reporter.register(JsonReportRenderer(out))
        assembler = ReportAssembler()

        collaborators = ScrapeCollaborators(
            preflight=lambda url: parse_robots("User-agent: *\nAllow: /", target=url),
            retriever=lambda ctx: [make_document(body=_HTML)],
            extractor=lambda docs: [make_extraction()],
            processor=lambda exts: make_dataset(count=1),
            persist=lambda ds, did, run: persistence.persist(ds, did, run_id=run),
            export=lambda ds, fmt, dest: exporter.export(ds, fmt, dest),
            report=lambda ds, fmt, dest: reporter.render(assembler.assemble(ds), fmt, dest),
            dataset_id="catalog",
            export_formats=("csv", "json"),
            report_formats=("html", "json"),
        )
        jobs = JobManager(
            SqlAlchemyJobStore(factory), clock=FrozenClock(), ids=SequentialIdGenerator()
        )
        checkpoints = CheckpointManager(
            SqlAlchemyCheckpointStore(factory),
            clock=FrozenClock(),
            ids=SequentialIdGenerator(),
            schema_version=1,
        )
        use_case = StartScrapeUseCase(
            jobs=jobs,
            checkpoints=checkpoints,
            ids=SequentialIdGenerator(),
            logger=RecordingLogger(),
        )
        outcome = use_case.execute(
            "https://catalog.example.com/", collaborators, correlation_id="corr-1"
        )

        assert outcome.job.state is JobState.COMPLETED
        assert outcome.job.dataset_ref == "catalog"
        assert outcome.job.dataset_version == 1
        assert len(persistence.history("catalog")) == 1
        produced = {p.name for p in out.iterdir()}
        assert any(name.endswith(".csv") for name in produced)
        assert any(name.endswith(".html") for name in produced)
        latest = checkpoints._store.latest(outcome.job.job_id)
        assert latest is not None
        assert latest.verify_integrity()

    def test_hard_stage_failure_fails_the_job(self, factory) -> None:  # type: ignore[no-untyped-def]
        def boom(ctx):  # type: ignore[no-untyped-def]
            raise RuntimeError("network down")

        from nexusai.domain.errors.exceptions import NetworkError

        def failing_retriever(ctx):  # type: ignore[no-untyped-def]
            raise NetworkError("network down")

        collaborators = ScrapeCollaborators(
            preflight=lambda url: parse_robots("User-agent: *\nAllow: /", target=url),
            retriever=failing_retriever,
            extractor=lambda docs: [make_extraction()],
            processor=lambda exts: make_dataset(count=1),
            persist=lambda ds, did, run: None,  # type: ignore[arg-type,return-value]
            export=lambda ds, fmt, dest: None,  # type: ignore[arg-type,return-value]
            report=lambda ds, fmt, dest: None,  # type: ignore[arg-type,return-value]
            dataset_id="catalog",
        )
        jobs = JobManager(
            SqlAlchemyJobStore(factory), clock=FrozenClock(), ids=SequentialIdGenerator()
        )
        checkpoints = CheckpointManager(
            SqlAlchemyCheckpointStore(factory),
            clock=FrozenClock(),
            ids=SequentialIdGenerator(),
            schema_version=1,
        )
        use_case = StartScrapeUseCase(
            jobs=jobs,
            checkpoints=checkpoints,
            ids=SequentialIdGenerator(),
            logger=RecordingLogger(),
        )
        outcome = use_case.execute("https://x/", collaborators, correlation_id="c")
        assert outcome.job.state is JobState.FAILED
        assert outcome.job.error_summary
