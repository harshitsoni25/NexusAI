"""Concrete rules for the rule engine.

A rule is a named, prioritised predicate over a record that reports a
:class:`~nexusai.domain.model.rules.RuleOutcome`. These implementations cover
the common shapes -- an arbitrary predicate, a numeric range, a regular
expression, and a conditional wrapper -- and each implements the
:class:`~nexusai.domain.ports.processing.Rule` port. Business rules are
expressed by composing these or by registering a custom rule; the engine treats
them all uniformly.

Rules carry a priority (lower runs first) and a group (so related rules can be
enabled together), and may decline to apply to a record, which is how conditional
evaluation is expressed without the engine knowing the condition.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from nexusai.domain.model.assessment import Severity
from nexusai.domain.model.processing import ProcessedRecord
from nexusai.domain.model.rules import RuleOutcome
from nexusai.shared.types import JsonValue

Predicate = Callable[[ProcessedRecord], bool]
"""A record predicate returning whether the rule holds."""

Condition = Callable[[ProcessedRecord], bool]
"""A record predicate returning whether a rule should be evaluated."""


class PredicateRule:
    """A rule that holds when a supplied predicate returns true.

    The general case: any business rule expressible as "this record is acceptable
    when ``predicate(record)``". More specific rules below exist for the common
    predicates so callers need not write them out.
    """

    def __init__(
        self,
        name: str,
        predicate: Predicate,
        *,
        message: str = "",
        priority: int = 100,
        group: str = "default",
        severity: Severity = Severity.ERROR,
        condition: Condition | None = None,
    ) -> None:
        self._name = name
        self._predicate = predicate
        self._message = message
        self._priority = priority
        self._group = group
        self._severity = severity
        self._condition = condition

    @property
    def name(self) -> str:
        """The rule's name."""
        return self._name

    @property
    def priority(self) -> int:
        """The evaluation priority; lower runs first."""
        return self._priority

    @property
    def group(self) -> str:
        """The rule's group."""
        return self._group

    @property
    def severity(self) -> Severity:
        """The severity of a failure."""
        return self._severity

    def applies(self, record: ProcessedRecord) -> bool:
        """Whether this rule should be evaluated against ``record``."""
        return self._condition is None or self._condition(record)

    def evaluate(self, record: ProcessedRecord) -> RuleOutcome:
        """Evaluate the predicate and return the outcome."""
        passed = bool(self._predicate(record))
        return RuleOutcome(
            rule=self._name,
            passed=passed,
            severity=self._severity,
            message="" if passed else (self._message or f"rule {self._name!r} failed"),
        )


class RangeRule(PredicateRule):
    """A rule that holds when a numeric field falls within a range."""

    def __init__(
        self,
        name: str,
        field: str,
        *,
        minimum: float | None = None,
        maximum: float | None = None,
        priority: int = 100,
        group: str = "default",
        severity: Severity = Severity.ERROR,
    ) -> None:
        def predicate(record: ProcessedRecord) -> bool:
            actual = record.value(field)
            if not isinstance(actual, (int, float)) or isinstance(actual, bool):
                return False
            if minimum is not None and actual < minimum:
                return False
            return not (maximum is not None and actual > maximum)

        super().__init__(
            name,
            predicate,
            message=f"field {field!r} is outside the allowed range",
            priority=priority,
            group=group,
            severity=severity,
        )
        self._location = field

    def evaluate(self, record: ProcessedRecord) -> RuleOutcome:
        """Evaluate the range and attach the field as the outcome location."""
        outcome = super().evaluate(record)
        return RuleOutcome(
            rule=outcome.rule,
            passed=outcome.passed,
            severity=outcome.severity,
            message=outcome.message,
            location=self._location,
        )


class RegexRule(PredicateRule):
    """A rule that holds when a string field matches a pattern."""

    def __init__(
        self,
        name: str,
        field: str,
        pattern: str,
        *,
        priority: int = 100,
        group: str = "default",
        severity: Severity = Severity.ERROR,
    ) -> None:
        compiled = re.compile(pattern)

        def predicate(record: ProcessedRecord) -> bool:
            actual = record.value(field)
            return isinstance(actual, str) and compiled.match(actual) is not None

        super().__init__(
            name,
            predicate,
            message=f"field {field!r} does not match {pattern!r}",
            priority=priority,
            group=group,
            severity=severity,
        )


def field_equals(field: str, expected: JsonValue) -> Predicate:
    """Return a predicate that holds when ``field`` equals ``expected``."""

    def predicate(record: ProcessedRecord) -> bool:
        return record.value(field) == expected

    return predicate


def field_present(field: str) -> Condition:
    """Return a condition that holds when ``field`` has a non-empty value."""

    def condition(record: ProcessedRecord) -> bool:
        value = record.value(field)
        return value is not None and not (isinstance(value, str) and not value.strip())

    return condition


__all__ = [
    "Condition",
    "Predicate",
    "PredicateRule",
    "RangeRule",
    "RegexRule",
    "field_equals",
    "field_present",
]
