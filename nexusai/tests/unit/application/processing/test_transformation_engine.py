"""Tests for the transformation engine and raw preservation."""

from __future__ import annotations

import pytest

from nexusai.application.processing.transformation import (
    TransformationEngine,
    TransformationPlan,
)
from nexusai.domain.errors.exceptions import TransformationError
from nexusai.domain.model.extraction import (
    ExtractedValue,
    ExtractionMethod,
    ExtractionResult,
    FieldProvenance,
)
from nexusai.domain.ports.processing import Transformer
from nexusai.infrastructure.normalization.transformers import (
    NumericNormalizer,
    WhitespaceCleaner,
)
from nexusai.shared.registry import Registry
from nexusai.shared.types import JsonValue


def _registry() -> Registry[Transformer]:
    registry: Registry[Transformer] = Registry("transformer")
    registry.register("whitespace", WhitespaceCleaner())
    registry.register("numeric", NumericNormalizer())
    return registry


def _extraction(**values: JsonValue) -> ExtractionResult:
    prov = FieldProvenance(method=ExtractionMethod.CSS)
    return ExtractionResult(
        fields={
            name: ExtractedValue(value=value, provenance=prov) for name, value in values.items()
        }
    )


def test_transform_applies_chain_and_preserves_raw() -> None:
    engine = TransformationEngine(_registry())
    extraction = _extraction(price=" $1,299.00 ", name="  Widget  ")
    plan = TransformationPlan(chains={"price": ["whitespace", "numeric"], "name": ["whitespace"]})
    record = engine.transform(extraction, plan)
    assert record.value("price") == 1299
    assert record.fields["price"].raw_value == " $1,299.00 "
    assert record.fields["price"].transformations == ("whitespace", "numeric")
    # The source extraction is preserved untouched.
    assert record.raw is extraction
    assert record.raw.value("price") == " $1,299.00 "


def test_unplanned_fields_carry_through() -> None:
    engine = TransformationEngine(_registry())
    record = engine.transform(_extraction(sku="AB1"), TransformationPlan())
    assert record.value("sku") == "AB1"
    assert record.fields["sku"].transformations == ()


def test_identity_from_field() -> None:
    engine = TransformationEngine(_registry())
    record = engine.transform(
        _extraction(id="p-42", name="X"), TransformationPlan(identity_field="id")
    )
    assert record.identity == "p-42"


def test_identity_falls_back_to_hash() -> None:
    engine = TransformationEngine(_registry())
    record = engine.transform(_extraction(name="X"), TransformationPlan())
    assert len(record.identity) == 64  # sha256 hex digest


def test_unknown_transformer_raises() -> None:
    engine = TransformationEngine(_registry())
    plan = TransformationPlan(chains={"price": ["nonexistent"]})
    with pytest.raises(TransformationError):
        engine.transform(_extraction(price="1"), plan)
