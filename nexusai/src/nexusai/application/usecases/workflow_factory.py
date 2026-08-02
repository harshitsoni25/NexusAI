"""Builds the standard scraping workflow definition and its stage set.

The standard workflow is the ordered spine of a scrape: initialise, preflight,
resolve a strategy, retrieve, extract, process, validate, persist, export, report,
finalise. This factory turns a bundle of injected collaborators -- the retrieval,
extraction and processing callables, the Phase 6 services, the preflight function
-- into that workflow, wiring each stage to the capability that does its work.

Keeping the assembly here, out of the orchestrator, is what lets the orchestrator
stay generic and the stages stay thin. A different workflow is a different
factory, not a change to either.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from nexusai.application.workflow.stage import WorkflowStage
from nexusai.application.workflow.stages import (
    ExportStage,
    Extractor,
    ExtractStage,
    FinalizeStage,
    InitializeStage,
    PersistStage,
    Preflighter,
    PreflightStage,
    Processor,
    ProcessStage,
    ReportStage,
    Retriever,
    RetrieveStage,
    StrategyStage,
    ValidateStage,
)
from nexusai.domain.model.analysis import RetrievalStrategy
from nexusai.domain.model.persistence import (
    DatasetVersion,
    ExportManifest,
    ReportManifest,
)
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.domain.model.workflow import (
    FailurePolicy,
    StageDefinition,
    WorkflowDefinition,
)

WORKFLOW_VERSION = "1"


@dataclass(frozen=True, slots=True, kw_only=True)
class ScrapeCollaborators:
    """The capabilities the standard scrape workflow delegates to."""

    preflight: Preflighter
    retriever: Retriever
    extractor: Extractor
    processor: Processor
    persist: Callable[[ProcessedDataset, str, str | None], DatasetVersion]
    export: Callable[[ProcessedDataset, str, str], ExportManifest]
    report: Callable[[ProcessedDataset, str, str], ReportManifest]
    dataset_id: str
    export_formats: tuple[str, ...] = ("csv", "json")
    report_formats: tuple[str, ...] = ("html", "json")
    strategy_override: RetrievalStrategy | None = None
    require_valid: bool = False
    allow_when_disallowed: bool = False


def standard_scrape_workflow() -> WorkflowDefinition:
    """Return the standard scraping workflow definition."""
    return WorkflowDefinition(
        name="scrape",
        version=WORKFLOW_VERSION,
        stages=[
            StageDefinition(name="initialize"),
            StageDefinition(
                name="preflight",
                depends_on=["initialize"],
                failure_policy=FailurePolicy.FAIL,
            ),
            StageDefinition(name="strategy", depends_on=["preflight"]),
            StageDefinition(name="retrieve", depends_on=["strategy"]),
            StageDefinition(name="extract", depends_on=["retrieve"]),
            StageDefinition(name="process", depends_on=["extract"], checkpoint_after=True),
            StageDefinition(name="validate", depends_on=["process"]),
            StageDefinition(name="persist", depends_on=["validate"], checkpoint_after=True),
            StageDefinition(
                name="export",
                depends_on=["persist"],
                optional=True,
                failure_policy=FailurePolicy.PARTIAL,
            ),
            StageDefinition(
                name="report",
                depends_on=["persist"],
                optional=True,
                failure_policy=FailurePolicy.PARTIAL,
            ),
            StageDefinition(name="finalize", depends_on=["persist"]),
        ],
    )


def build_scrape_stages(collaborators: ScrapeCollaborators) -> dict[str, WorkflowStage]:
    """Build the stage implementations for the standard scrape workflow."""
    return {
        "initialize": InitializeStage(),
        "preflight": PreflightStage(
            collaborators.preflight,
            allow_when_disallowed=collaborators.allow_when_disallowed,
        ),
        "strategy": StrategyStage(override=collaborators.strategy_override),
        "retrieve": RetrieveStage(collaborators.retriever),
        "extract": ExtractStage(collaborators.extractor),
        "process": ProcessStage(collaborators.processor),
        "validate": ValidateStage(require_valid=collaborators.require_valid),
        "persist": PersistStage(
            collaborators.persist,
            dataset_id=collaborators.dataset_id,
        ),
        "export": ExportStage(
            collaborators.export,
            formats=collaborators.export_formats,
        ),
        "report": ReportStage(
            collaborators.report,
            formats=collaborators.report_formats,
        ),
        "finalize": FinalizeStage(),
    }
