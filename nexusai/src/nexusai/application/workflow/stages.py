"""The concrete stages of the standard scraping workflow.

Each stage is a thin adapter: it reads what it needs from the context and
workspace, delegates the real work to a collaborator supplied at construction --
a retrieval function, an extraction function, a Phase 6 service -- and records its
output. None of them implements retrieval, extraction, processing, persistence,
export or reporting; they route to the engines and services that do.

The collaborators are narrow callables and service objects rather than the full
engines, so a stage can be tested with a trivial fake and the composition root
decides what real implementation stands behind each one.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from nexusai.application.runtime.context import ExecutionContext
from nexusai.application.workflow.stage import Workspace
from nexusai.domain.errors.exceptions import NexusAIError, ValidationError
from nexusai.domain.model.analysis import AnalysisResult, RetrievalStrategy
from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.domain.model.retrieval import Document
from nexusai.domain.policy.strategy_recommendation import (
    apply_override,
    recommend_strategy,
)

# Workspace keys shared between stages.
DOCUMENTS = "documents"
EXTRACTIONS = "extractions"
DATASET = "dataset"
ANALYSIS = "analysis"
PREFLIGHT = "preflight"
RECOMMENDATION = "recommendation"

Retriever = Callable[[ExecutionContext], Sequence[Document]]
Extractor = Callable[[Sequence[Document]], Sequence[ExtractionResult]]
Processor = Callable[[Sequence[ExtractionResult]], ProcessedDataset]
Analyzer = Callable[[ExecutionContext, Workspace], AnalysisResult]
Preflighter = Callable[[str], object]


class InitializeStage:
    """Marks the start of the workflow. Always succeeds."""

    name = "initialize"

    def can_run(self, context: ExecutionContext, workspace: Workspace) -> bool:
        """Report whether this stage's preconditions are met."""
        return True

    def execute(self, context: ExecutionContext, workspace: Workspace) -> ExecutionContext:
        """Perform the stage and return the updated context."""
        return context


class PreflightStage:
    """Runs responsible target preflight (robots.txt) via a collaborator.

    Failure here is a warning, not a stopper, unless the preflight result marks
    the target as disallowed, in which case the stage raises so the workflow can
    honour the site's stated wishes.
    """

    name = "preflight"

    def __init__(self, preflight: Preflighter, *, allow_when_disallowed: bool = False) -> None:
        self._preflight = preflight
        self._allow = allow_when_disallowed

    def can_run(self, context: ExecutionContext, workspace: Workspace) -> bool:
        """Report whether this stage's preconditions are met."""
        return True

    def execute(self, context: ExecutionContext, workspace: Workspace) -> ExecutionContext:
        """Perform the stage and return the updated context."""
        result = self._preflight(context.target)
        workspace.put(PREFLIGHT, result)
        allowed = getattr(result, "allowed", True)
        if not allowed and not self._allow:
            raise NexusAIError(
                "Target preflight disallows scraping this path", target=context.target
            )
        return context


class AnalysisStage:
    """Optionally analyses the target's observable characteristics."""

    name = "analyze"

    def __init__(self, analyzer: Analyzer) -> None:
        self._analyzer = analyzer

    def can_run(self, context: ExecutionContext, workspace: Workspace) -> bool:
        """Report whether this stage's preconditions are met."""
        return True

    def execute(self, context: ExecutionContext, workspace: Workspace) -> ExecutionContext:
        """Perform the stage and return the updated context."""
        analysis = self._analyzer(context, workspace)
        workspace.put(ANALYSIS, analysis)
        return context


class StrategyStage:
    """Resolves the retrieval strategy from analysis, honouring any override."""

    name = "strategy"

    def __init__(self, *, override: RetrievalStrategy | None = None) -> None:
        self._override = override

    def can_run(self, context: ExecutionContext, workspace: Workspace) -> bool:
        """Report whether this stage's preconditions are met."""
        return True

    def execute(self, context: ExecutionContext, workspace: Workspace) -> ExecutionContext:
        """Perform the stage and return the updated context."""
        analysis = workspace.get(ANALYSIS)
        if isinstance(analysis, AnalysisResult):
            recommendation = recommend_strategy(analysis)
        else:
            from nexusai.domain.model.analysis import Confidence, StrategyRecommendation

            recommendation = StrategyRecommendation(
                strategy=RetrievalStrategy.HTTP,
                confidence=Confidence.LOW,
                rationale="no analysis available; defaulting to HTTP",
            )
        if self._override is not None:
            recommendation = apply_override(recommendation, self._override)
        workspace.put(RECOMMENDATION, recommendation)
        return context.with_strategy(recommendation.strategy)


class RetrieveStage:
    """Retrieves documents via the retrieval collaborator."""

    name = "retrieve"

    def __init__(self, retriever: Retriever) -> None:
        self._retriever = retriever

    def can_run(self, context: ExecutionContext, workspace: Workspace) -> bool:
        """Report whether this stage's preconditions are met."""
        return True

    def execute(self, context: ExecutionContext, workspace: Workspace) -> ExecutionContext:
        """Perform the stage and return the updated context."""
        documents = list(self._retriever(context))
        if not documents:
            raise NexusAIError("Retrieval produced no documents", target=context.target)
        workspace.put(DOCUMENTS, documents)
        return context


class ExtractStage:
    """Extracts structured values from retrieved documents."""

    name = "extract"

    def __init__(self, extractor: Extractor) -> None:
        self._extractor = extractor

    def can_run(self, context: ExecutionContext, workspace: Workspace) -> bool:
        """Report whether this stage's preconditions are met."""
        return workspace.has(DOCUMENTS)

    def execute(self, context: ExecutionContext, workspace: Workspace) -> ExecutionContext:
        """Perform the stage and return the updated context."""
        documents = workspace.require(DOCUMENTS)
        assert isinstance(documents, list)
        extractions = list(self._extractor(documents))
        workspace.put(EXTRACTIONS, extractions)
        return context


class ProcessStage:
    """Processes extraction results into a validated, assessed dataset."""

    name = "process"

    def __init__(self, processor: Processor) -> None:
        self._processor = processor

    def can_run(self, context: ExecutionContext, workspace: Workspace) -> bool:
        """Report whether this stage's preconditions are met."""
        return workspace.has(EXTRACTIONS)

    def execute(self, context: ExecutionContext, workspace: Workspace) -> ExecutionContext:
        """Perform the stage and return the updated context."""
        extractions = workspace.require(EXTRACTIONS)
        assert isinstance(extractions, list)
        dataset = self._processor(extractions)
        workspace.put(DATASET, dataset)
        return context


class ValidateStage:
    """Checks the processed dataset meets a minimum validity threshold.

    Validation and quality assessment already ran in processing; this stage only
    *inspects* their results and decides whether the dataset is acceptable. It
    raises a :class:`ValidationError` when the dataset is invalid, which -- under a
    ``PARTIAL`` failure policy -- turns a materially incomplete result into a
    ``PARTIAL`` job rather than a clean success.
    """

    name = "validate"

    def __init__(self, *, require_valid: bool = False) -> None:
        self._require_valid = require_valid

    def can_run(self, context: ExecutionContext, workspace: Workspace) -> bool:
        """Report whether this stage's preconditions are met."""
        return workspace.has(DATASET)

    def execute(self, context: ExecutionContext, workspace: Workspace) -> ExecutionContext:
        """Perform the stage and return the updated context."""
        dataset = workspace.require(DATASET)
        assert isinstance(dataset, ProcessedDataset)
        if self._require_valid and not dataset.is_valid:
            raise ValidationError(
                "Dataset did not meet the required validity threshold",
                records=len(dataset),
            )
        return context


class PersistStage:
    """Persists the dataset through the Phase 6 persistence service."""

    name = "persist"

    def __init__(
        self, persist: Callable[[ProcessedDataset, str, str | None], object], *, dataset_id: str
    ) -> None:
        self._persist = persist
        self._dataset_id = dataset_id

    def can_run(self, context: ExecutionContext, workspace: Workspace) -> bool:
        """Report whether this stage's preconditions are met."""
        return workspace.has(DATASET)

    def execute(self, context: ExecutionContext, workspace: Workspace) -> ExecutionContext:
        """Perform the stage and return the updated context."""
        dataset = workspace.require(DATASET)
        assert isinstance(dataset, ProcessedDataset)
        version = self._persist(dataset, self._dataset_id, context.job_id)
        version_number = int(getattr(version, "version", 1))
        return context.with_dataset(self._dataset_id, version_number)


class ExportStage:
    """Exports the dataset in the requested formats via the export service."""

    name = "export"

    def __init__(
        self,
        export: Callable[[ProcessedDataset, str, str], object],
        *,
        formats: Sequence[str],
    ) -> None:
        self._export = export
        self._formats = tuple(formats)

    def can_run(self, context: ExecutionContext, workspace: Workspace) -> bool:
        """Report whether this stage's preconditions are met."""
        return workspace.has(DATASET) and bool(self._formats)

    def execute(self, context: ExecutionContext, workspace: Workspace) -> ExecutionContext:
        """Perform the stage and return the updated context."""
        dataset = workspace.require(DATASET)
        assert isinstance(dataset, ProcessedDataset)
        updated = context
        for export_format in self._formats:
            destination = f"{context.job_id}.{export_format}"
            manifest = self._export(dataset, export_format, destination)
            updated = updated.with_export(str(getattr(manifest, "export_id", destination)))
        return updated


class ReportStage:
    """Builds and renders reports via the Phase 6 assembler and report service."""

    name = "report"

    def __init__(
        self,
        report: Callable[[ProcessedDataset, str, str], object],
        *,
        formats: Sequence[str],
    ) -> None:
        self._report = report
        self._formats = tuple(formats)

    def can_run(self, context: ExecutionContext, workspace: Workspace) -> bool:
        """Report whether this stage's preconditions are met."""
        return workspace.has(DATASET) and bool(self._formats)

    def execute(self, context: ExecutionContext, workspace: Workspace) -> ExecutionContext:
        """Perform the stage and return the updated context."""
        dataset = workspace.require(DATASET)
        assert isinstance(dataset, ProcessedDataset)
        updated = context
        for report_format in self._formats:
            destination = f"{context.job_id}-report.{report_format}"
            manifest = self._report(dataset, report_format, destination)
            updated = updated.with_report(str(getattr(manifest, "report_id", destination)))
        return updated


class FinalizeStage:
    """Marks the workflow complete. Always succeeds."""

    name = "finalize"

    def can_run(self, context: ExecutionContext, workspace: Workspace) -> bool:
        """Report whether this stage's preconditions are met."""
        return True

    def execute(self, context: ExecutionContext, workspace: Workspace) -> ExecutionContext:
        """Perform the stage and return the updated context."""
        return context
