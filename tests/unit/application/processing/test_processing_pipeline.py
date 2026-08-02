"""End-to-end tests for the processing pipeline."""

from __future__ import annotations

from nexusai.application.processing.change import ChangeDetectionEngine
from nexusai.application.processing.pipeline import (
    ProcessingPipeline,
    ProcessingRequest,
)
from nexusai.application.processing.quality import QualityEngine
from nexusai.application.processing.rules import RuleEngine
from nexusai.application.processing.transformation import (
    TransformationEngine,
    TransformationPlan,
)
from nexusai.application.processing.validation import ValidationEngine
from nexusai.domain.model.extraction import (
    ExtractedValue,
    ExtractionMethod,
    ExtractionResult,
    FieldProvenance,
)
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.domain.model.quality import QualityGrade
from nexusai.domain.ports.processing import Transformer
from nexusai.infrastructure.change.detectors import FieldDiffDetector
from nexusai.infrastructure.normalization.transformers import (
    NumericNormalizer,
    WhitespaceCleaner,
)
from nexusai.infrastructure.quality.dimensions import (
    AccuracyDimension,
    CompletenessDimension,
)
from nexusai.infrastructure.rules.rules import RangeRule
from nexusai.infrastructure.validation.validators import (
    RequiredFieldsValidator,
    TypeValidator,
)
from nexusai.shared.registry import Registry
from nexusai.testing import FrozenClock


def _pipeline() -> ProcessingPipeline:
    transformers: Registry[Transformer] = Registry("transformer")
    transformers.register("whitespace", WhitespaceCleaner())
    transformers.register("numeric", NumericNormalizer())
    return ProcessingPipeline(
        TransformationEngine(transformers),
        ValidationEngine(
            [RequiredFieldsValidator(["name", "price"]), TypeValidator({"price": (int, float)})]
        ),
        RuleEngine([RangeRule("price-range", "price", minimum=0, maximum=1000)]),
        QualityEngine([CompletenessDimension(["name", "price"]), AccuracyDimension()]),
        ChangeDetectionEngine([FieldDiffDetector()]),
        clock=FrozenClock(),
        framework_version="9.9.9",
    )


def _extraction(name: str, price: str) -> ExtractionResult:
    prov = FieldProvenance(method=ExtractionMethod.CSS)
    return ExtractionResult(
        fields={
            "name": ExtractedValue(value=name, provenance=prov),
            "price": ExtractedValue(value=price, provenance=prov),
        }
    )


def _plan() -> TransformationPlan:
    return TransformationPlan(
        chains={"name": ["whitespace"], "price": ["whitespace", "numeric"]},
        identity_field="name",
    )


def test_pipeline_produces_processed_dataset() -> None:
    request = ProcessingRequest(
        extractions=[_extraction("  Widget  ", " $19.99 "), _extraction("Gadget", "$5")],
        plan=_plan(),
        rule_version="v1",
    )
    dataset = _pipeline().run(request)
    assert len(dataset) == 2
    first = dataset.records[0]
    # Transformation applied, raw preserved.
    assert first.value("price") == 19.99
    assert first.fields["price"].raw_value == " $19.99 "
    assert first.value("name") == "Widget"
    # Validation ran and passed.
    assert first.validation.is_valid is True
    # Context assembled.
    assert dataset.context is not None
    assert dataset.context.framework_version == "9.9.9"
    assert dataset.context.rule_version == "v1"
    assert dataset.context.quality_grade is QualityGrade.A


def test_pipeline_preserves_raw_extraction() -> None:
    extraction = _extraction("X", " $5 ")
    request = ProcessingRequest(extractions=[extraction], plan=_plan())
    dataset = _pipeline().run(request)
    # The original extraction object is retained unchanged.
    assert dataset.records[0].raw is extraction
    assert dataset.records[0].raw.value("price") == " $5 "


def test_pipeline_flags_invalid_records() -> None:
    # Missing price; violates required-fields and the range rule cannot apply.
    prov = FieldProvenance(method=ExtractionMethod.CSS)
    extraction = ExtractionResult(fields={"name": ExtractedValue(value="X", provenance=prov)})
    request = ProcessingRequest(extractions=[extraction], plan=_plan())
    dataset = _pipeline().run(request)
    assert dataset.is_valid is False
    assert dataset.context is not None
    assert dataset.context.validation_summary.is_valid is False


def test_pipeline_detects_change_against_previous() -> None:
    pipeline = _pipeline()
    first = pipeline.run(
        ProcessingRequest(extractions=[_extraction("Widget", "$10")], plan=_plan())
    )
    second = pipeline.run(
        ProcessingRequest(extractions=[_extraction("Widget", "$15")], plan=_plan(), previous=first)
    )
    assert second.context is not None
    assert second.context.change_summary.modified == 1


def test_pipeline_without_previous_reports_no_change() -> None:
    dataset = _pipeline().run(ProcessingRequest(extractions=[_extraction("X", "$1")], plan=_plan()))
    assert dataset.context is not None
    assert dataset.context.change_summary.total == 0


def test_pipeline_with_no_extractions() -> None:
    dataset = _pipeline().run(ProcessingRequest(extractions=[]))
    assert isinstance(dataset, ProcessedDataset)
    assert len(dataset) == 0
    assert dataset.context is not None
