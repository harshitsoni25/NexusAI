"""Tests for the rule engine's ordering, grouping and conditions."""

from __future__ import annotations

from nexusai.application.processing.rules import RuleEngine
from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import ProcessedField, ProcessedRecord
from nexusai.infrastructure.rules.rules import (
    Predicate,
    PredicateRule,
    RangeRule,
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


def test_engine_aggregates_failures() -> None:
    engine = RuleEngine([RangeRule("price", "price", maximum=10)])
    result, outcomes = engine.evaluate(_record(price=50))
    assert result.is_valid is False
    assert outcomes[0].passed is False


def test_engine_runs_in_priority_order() -> None:
    seen: list[str] = []

    def record_call(name: str) -> Predicate:
        def predicate(_record: ProcessedRecord) -> bool:
            seen.append(name)
            return True

        return predicate

    engine = RuleEngine(
        [
            PredicateRule("low-priority", record_call("low"), priority=200),
            PredicateRule("high-priority", record_call("high"), priority=1),
        ]
    )
    engine.evaluate(_record(x=1))
    assert seen == ["high", "low"]


def test_engine_filters_by_group() -> None:
    engine = RuleEngine(
        [
            PredicateRule("a", field_equals("x", 1), group="core"),
            PredicateRule("b", field_equals("x", 2), group="business", message="fail"),
        ]
    )
    _result, outcomes = engine.evaluate(_record(x=1), group="core")
    assert [outcome.rule for outcome in outcomes] == ["a"]


def test_engine_skips_inapplicable_rules() -> None:
    engine = RuleEngine(
        [
            PredicateRule(
                "when-present",
                field_equals("status", "active"),
                condition=field_present("status"),
            )
        ]
    )
    _result, outcomes = engine.evaluate(_record(other=1))
    assert outcomes == ()
