"""The change-detection engine.

Runs a set of detectors comparing a current dataset against a previous one and
collects their change sets. Running several detectors together lets a caller ask
different questions at once -- membership, field values, structure -- and receive
each detector's answer, plus a combined summary for the processing context.
"""

from __future__ import annotations

from collections.abc import Sequence

from nexusai.domain.model.change import ChangeSet, ChangeSummary
from nexusai.domain.model.processing import ProcessedDataset
from nexusai.domain.ports.processing import ChangeDetector


class ChangeDetectionEngine:
    """Runs change detectors over a pair of datasets."""

    def __init__(self, detectors: Sequence[ChangeDetector]) -> None:
        self._detectors = tuple(detectors)

    def detect(
        self, current: ProcessedDataset, previous: ProcessedDataset
    ) -> tuple[Sequence[ChangeSet], ChangeSummary]:
        """Run every detector and return the change sets and a combined summary."""
        change_sets = [detector.detect(current, previous) for detector in self._detectors]
        return tuple(change_sets), ChangeSummary.from_change_sets(change_sets)
