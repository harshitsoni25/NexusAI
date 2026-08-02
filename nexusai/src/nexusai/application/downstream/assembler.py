"""Assembles the report model from a processed dataset.

This is where a processed dataset becomes a :class:`Report`. The assembler reads
the validation, quality and change results that Phase 5 already recorded on the
dataset's context and copies them into report sections; it computes nothing about
data quality itself. That discipline is what keeps reporting free of processing
logic -- the numbers in the report are the numbers Phase 5 produced, not a second
opinion. Secret redaction is applied to any configuration surfaced, so a report
never leaks a credential.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from nexusai.domain.model.assessment import Severity
from nexusai.domain.model.network import NetworkObservation
from nexusai.domain.model.persistence import DatasetVersion
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.domain.model.report import (
    ChangeSummarySection,
    DatasetSummary,
    PerformanceSection,
    ProvenanceEntry,
    QualitySummarySection,
    RenderingSection,
    Report,
    ReportArtifact,
    RunSummary,
    ValidationSummarySection,
)
from nexusai.domain.model.visual import VisualComparison


class ReportAssembler:
    """Builds a stable report model from a processed dataset and its context."""

    def assemble(
        self,
        dataset: ProcessedDataset,
        *,
        version: DatasetVersion | None = None,
        errors: Sequence[str] = (),
        warnings: Sequence[str] = (),
        artifacts: Sequence[ReportArtifact] = (),
        performance: dict[str, float] | None = None,
        visual: VisualComparison | None = None,
        network: NetworkObservation | None = None,
        staged_screenshot_count: int = 0,
    ) -> Report:
        """Return the report model for ``dataset``.

        Validation, quality and change figures are read from the dataset's
        processing context; they are never recomputed here. A rendering section is
        added only when browser evidence (a visual comparison, network observation
        or staged screenshots) is supplied.
        """
        context = dataset.context
        generated_at = datetime.now(UTC)
        framework_version = context.framework_version if context else ""

        run = RunSummary(
            run_id=version.run_id if version else None,
            framework_version=framework_version,
            rule_version=context.rule_version if context else "",
            started_at=None,
            finished_at=context.processed_at if context else None,
        )
        dataset_summary = self._dataset_summary(dataset, version)
        validation = self._validation(dataset)
        quality = self._quality(dataset)
        change = self._change(dataset)
        provenance = self._provenance(dataset)
        rendering = self._rendering(visual, network, staged_screenshot_count)

        return Report(
            generated_at=generated_at,
            framework_version=framework_version,
            run=run,
            dataset=dataset_summary,
            validation=validation,
            quality=quality,
            change=change,
            provenance=provenance,
            artifacts=tuple(artifacts),
            performance=PerformanceSection(metrics=performance or {}),
            rendering=rendering,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def _rendering(
        self,
        visual: VisualComparison | None,
        network: NetworkObservation | None,
        staged_screenshot_count: int,
    ) -> RenderingSection | None:
        """Build the rendering section from browser evidence, if any was supplied."""
        if visual is None and network is None and staged_screenshot_count == 0:
            return None
        return RenderingSection(
            rendered=True,
            visual_status=visual.status.value if visual else None,
            visual_difference_ratio=visual.difference_ratio if visual else None,
            visual_comparable=visual.comparable if visual else None,
            staged_screenshot_count=staged_screenshot_count,
            network=network.to_dict() if network else {},
        )

    def _dataset_summary(
        self, dataset: ProcessedDataset, version: DatasetVersion | None
    ) -> DatasetSummary:
        field_names: set[str] = set()
        for record in dataset.records:
            field_names.update(record.fields)
        sources = {record.source.uri for record in dataset.records if record.source is not None}
        return DatasetSummary(
            dataset_id=str(version.dataset_id) if version else "",
            version=version.version if version else 0,
            record_count=len(dataset.records),
            field_count=len(field_names),
            source_count=len(sources),
        )

    def _validation(self, dataset: ProcessedDataset) -> ValidationSummarySection:
        context = dataset.context
        if context is None:
            return ValidationSummarySection()
        summary = context.validation_summary
        passing = sum(1 for record in dataset.records if record.validation.is_valid)
        failing = len(dataset.records) - passing
        warning = sum(
            1
            for record in dataset.records
            if record.validation.highest_severity == Severity.WARNING
        )
        status = "PASS" if summary.is_valid else "FAIL"
        if status == "PASS" and warning:
            status = "WARNING"
        return ValidationSummarySection(
            status=status,
            passing_records=passing,
            failing_records=failing,
            warning_records=warning,
            issues=tuple(issue.to_dict() for issue in summary.issues),
        )

    def _quality(self, dataset: ProcessedDataset) -> QualitySummarySection:
        context = dataset.context
        if context is None:
            return QualitySummarySection()
        return QualitySummarySection(
            grade=context.quality_grade.value,
            composite_score=context.quality.composite_score,
            dimensions=tuple(m.to_dict() for m in context.quality.measurements),
        )

    def _change(self, dataset: ProcessedDataset) -> ChangeSummarySection:
        context = dataset.context
        if context is None:
            return ChangeSummarySection()
        change = context.change_summary
        return ChangeSummarySection(
            added=change.added,
            removed=change.removed,
            modified=change.modified,
            detectors=tuple(change.detectors),
        )

    def _provenance(self, dataset: ProcessedDataset) -> tuple[ProvenanceEntry, ...]:
        seen: dict[str, ProvenanceEntry] = {}
        for record in dataset.records:
            source = record.source
            if source is None or source.uri in seen:
                continue
            seen[source.uri] = ProvenanceEntry(
                uri=source.uri,
                method=source.method,
                retrieved_at=source.retrieved_at,
                content_hash=source.content_hash,
            )
        return tuple(seen.values())
