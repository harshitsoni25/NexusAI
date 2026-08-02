"""The processing pipeline: the fixed sequence, with replaceable stages.

The pipeline runs the phase's mandated order -- transform, validate, evaluate
rules, assess quality, detect change -- and assembles the result into a
:class:`ProcessedDataset` with a :class:`ProcessingContext` describing how it was
produced. Each engine is injected, so any stage can be replaced or omitted: a run
that needs no change detection simply passes no previous dataset, and a caller
with a bespoke quality engine passes it in.

The pipeline itself holds no processing logic. It is the conductor -- it decides
the order and threads the growing result through the engines -- while every
decision about *how* to transform, validate, score or compare lives in the
engines and the strategies they run. That separation is what keeps the mandated
sequence readable in one place and each stage independently testable.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from nexusai.application.processing.change import ChangeDetectionEngine
from nexusai.application.processing.quality import QualityEngine
from nexusai.application.processing.rules import RuleEngine
from nexusai.application.processing.transformation import (
    TransformationEngine,
    TransformationPlan,
)
from nexusai.application.processing.validation import ValidationEngine
from nexusai.domain.model.assessment import ValidationResult
from nexusai.domain.model.change import ChangeSummary
from nexusai.domain.model.execution import ConfigurationSnapshot
from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import (
    ProcessedDataset,
    ProcessedRecord,
    ProcessingContext,
)
from nexusai.domain.ports.observability import Clock


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessingRequest:
    """The inputs to a processing run.

    Attributes:
        extractions: The raw extraction results to process, one per record.
        plan: The transformation plan applied to every extraction.
        previous: The prior dataset to compare against for change detection, or
            ``None`` to skip change detection.
        rule_group: When set, only rules in this group are evaluated.
        configuration: A snapshot of the effective configuration, recorded on the
            context.
        rule_version: The version label of the rule configuration.
    """

    extractions: Sequence[ExtractionResult]
    plan: TransformationPlan = field(default_factory=TransformationPlan)
    previous: ProcessedDataset | None = None
    rule_group: str | None = None
    configuration: ConfigurationSnapshot = field(default_factory=ConfigurationSnapshot)
    rule_version: str = "unversioned"


class ProcessingPipeline:
    """Sequences the processing engines into the mandated order."""

    def __init__(
        self,
        transformation: TransformationEngine,
        validation: ValidationEngine,
        rules: RuleEngine,
        quality: QualityEngine,
        change: ChangeDetectionEngine,
        *,
        clock: Clock,
        framework_version: str = "0.1.0",
    ) -> None:
        self._transformation = transformation
        self._validation = validation
        self._rules = rules
        self._quality = quality
        self._change = change
        self._clock = clock
        self._version = framework_version

    def run(self, request: ProcessingRequest) -> ProcessedDataset:
        """Process every extraction and return the assembled dataset."""
        records = [
            self._process_record(extraction, request.plan, request.rule_group)
            for extraction in request.extractions
        ]
        dataset = ProcessedDataset(records=records)

        quality_result, grade = self._quality.assess(dataset)
        _change_sets, change_summary = (
            self._change.detect(dataset, request.previous)
            if request.previous is not None
            else ((), _empty_summary())
        )
        context = ProcessingContext(
            processed_at=self._clock.now(),
            framework_version=self._version,
            rule_version=request.rule_version,
            configuration=request.configuration,
            validation_summary=_summarise_validation(records),
            quality=quality_result,
            quality_grade=grade,
            change_summary=change_summary,
            sources=tuple(record.source for record in records if record.source is not None),
        )
        return dataset.with_context(context)

    def _process_record(
        self,
        extraction: ExtractionResult,
        plan: TransformationPlan,
        rule_group: str | None,
    ) -> ProcessedRecord:
        record = self._transformation.transform(extraction, plan)
        structural = self._validation.validate(record)
        rule_result, _outcomes = self._rules.evaluate(record, group=rule_group)
        return record.with_validation(structural.merge(rule_result))


def _summarise_validation(records: Sequence[ProcessedRecord]) -> ValidationResult:
    summary = ValidationResult.passing(checked=0)
    for record in records:
        summary = summary.merge(record.validation)
    return summary


def _empty_summary() -> ChangeSummary:
    return ChangeSummary()
