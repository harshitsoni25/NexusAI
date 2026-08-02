"""Tests for the concrete rule implementations."""

from __future__ import annotations

from nexusai.domain.model.assessment import Severity
from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import ProcessedField, ProcessedRecord
from nexusai.infrastructure.rules.rules import (
    PredicateRule,
    RangeRule,
    RegexRule,
    field_equals,
    field_present,
)
from nexusai.shared.types import JsonValue


def _record(**fields: JsonValue) -> ProcessedRecord:
    return ProcessedRecord(
        identity="r",
        raw=ExtractionResult(),
        fields={
            name: ProcessedField(name=name, value=value, raw_value=value)
            for name, value in fields.items()
        },
    )


def test_predicate_rule_passes_and_fails() -> None:
    rule = PredicateRule("has-name", field_equals("name", "X"), message="bad name")
    assert rule.evaluate(_record(name="X")).passed is True
    failed = rule.evaluate(_record(name="Y"))
    assert failed.passed is False
    assert failed.message == "bad name"


def test_predicate_rule_metadata() -> None:
    rule = PredicateRule(
        "r", field_equals("a", 1), priority=5, group="business", severity=Severity.WARNING
    )
    assert rule.priority == 5
    assert rule.group == "business"
    assert rule.severity is Severity.WARNING


def test_range_rule_bounds_and_location() -> None:
    rule = RangeRule("price-range", "price", minimum=0, maximum=100)
    assert rule.evaluate(_record(price=50)).passed is True
    failed = rule.evaluate(_record(price=150))
    assert failed.passed is False
    assert failed.location == "price"


def test_range_rule_rejects_non_numeric() -> None:
    assert RangeRule("r", "price", minimum=0).evaluate(_record(price="x")).passed is False


def test_regex_rule() -> None:
    rule = RegexRule("sku", "sku", r"^[A-Z]{2}-\d+$")
    assert rule.evaluate(_record(sku="AB-12")).passed is True
    assert rule.evaluate(_record(sku="lowercase")).passed is False


def test_conditional_rule_applies() -> None:
    rule = PredicateRule(
        "when-present",
        field_equals("status", "active"),
        condition=field_present("status"),
    )
    assert rule.applies(_record(status="active")) is True
    assert rule.applies(_record(other=1)) is False
    assert rule.applies(_record(status="  ")) is False


def test_predicate_rule_exposes_name() -> None:
    rule = PredicateRule("named-rule", field_equals("a", 1))
    assert rule.name == "named-rule"


def test_range_rule_open_ended_minimum_only() -> None:
    rule = RangeRule("min-only", "n", minimum=10)
    assert rule.evaluate(_record(n=5)).passed is False
    assert rule.evaluate(_record(n=20)).passed is True
