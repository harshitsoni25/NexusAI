"""The rule engine.

Runs rules over a record in priority order, skipping those that do not apply, and
aggregates their outcomes into a :class:`ValidationResult` so rule failures live
in the same report as structural findings. Priority ordering is stable: rules of
equal priority run in registration order, so a run is reproducible.

A rule group can be selected, letting a caller run only the business rules, or
only a named set, without rebuilding the engine.
"""

from __future__ import annotations

from collections.abc import Sequence

from nexusai.domain.model.assessment import ValidationResult
from nexusai.domain.model.processing import ProcessedRecord
from nexusai.domain.model.rules import RuleOutcome
from nexusai.domain.ports.processing import Rule


class RuleEngine:
    """Evaluates prioritised, grouped, conditional rules over a record."""

    def __init__(self, rules: Sequence[Rule]) -> None:
        # Stable sort by priority preserves registration order within a priority.
        self._rules = tuple(sorted(rules, key=lambda rule: rule.priority))

    def evaluate(
        self, record: ProcessedRecord, *, group: str | None = None
    ) -> tuple[ValidationResult, Sequence[RuleOutcome]]:
        """Evaluate applicable rules and return the result and every outcome.

        Args:
            record: The record to evaluate.
            group: When given, only rules in this group are evaluated.
        """
        outcomes: list[RuleOutcome] = []
        result = ValidationResult.passing(checked=0)
        for rule in self._rules:
            if group is not None and rule.group != group:
                continue
            if not rule.applies(record):
                continue
            outcome = rule.evaluate(record)
            outcomes.append(outcome)
            issue = outcome.as_issue()
            if issue is not None:
                result = result.merge(ValidationResult(issues=[issue], checked=1))
            else:
                result = result.merge(ValidationResult.passing(checked=1))
        return result, tuple(outcomes)
