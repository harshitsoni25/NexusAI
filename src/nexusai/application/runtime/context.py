"""The execution context threaded through a workflow.

The context carries the identities and references a run needs -- job, correlation,
workflow, effective configuration, target, and the growing set of result
references -- plus the cancellation token. It is deliberately a *reference*
carrier: datasets and documents are passed between stages as stage outputs, not
stuffed into the context, so the context stays small and there is no global
mutable execution state.

The context is immutable; a stage that learns something new (a dataset was
persisted, a checkpoint was written) returns a new context via one of the
``with_*`` helpers, so each stage sees a consistent snapshot and history is never
rewritten in place.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from nexusai.application.runtime.cancellation import CancellationToken
from nexusai.domain.model.analysis import RetrievalStrategy
from nexusai.shared.types import JsonValue


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionContext:
    """Immutable references and state carried through a workflow run.

    Attributes:
        job_id: The job being executed.
        correlation_id: The correlation identifier for tracing.
        workflow_version: The workflow definition version.
        target: The site or URL being scraped.
        configuration_ref: The effective configuration identity.
        adapter_name: The resolved site adapter, if any.
        strategy: The resolved retrieval strategy, if chosen.
        dataset_ref: The persisted dataset, once produced.
        dataset_version: The dataset version, once produced.
        checkpoint_ref: The latest checkpoint, once written.
        export_refs: References to exports produced.
        report_refs: References to reports produced.
        cancellation: The cooperative cancellation token.
        attributes: Free-form references a stage may pass forward.
    """

    job_id: str
    correlation_id: str
    workflow_version: str
    target: str
    configuration_ref: str | None = None
    adapter_name: str | None = None
    strategy: RetrievalStrategy | None = None
    dataset_ref: str | None = None
    dataset_version: int | None = None
    checkpoint_ref: str | None = None
    export_refs: tuple[str, ...] = ()
    report_refs: tuple[str, ...] = ()
    cancellation: CancellationToken = field(default_factory=CancellationToken)
    attributes: Mapping[str, JsonValue] = field(default_factory=dict)

    def with_strategy(self, strategy: RetrievalStrategy) -> ExecutionContext:
        """Return a copy with the resolved retrieval strategy set."""
        return replace(self, strategy=strategy)

    def with_adapter(self, adapter_name: str) -> ExecutionContext:
        """Return a copy with the resolved adapter name set."""
        return replace(self, adapter_name=adapter_name)

    def with_dataset(self, dataset_ref: str, dataset_version: int) -> ExecutionContext:
        """Return a copy recording the persisted dataset."""
        return replace(self, dataset_ref=dataset_ref, dataset_version=dataset_version)

    def with_checkpoint(self, checkpoint_ref: str) -> ExecutionContext:
        """Return a copy recording the latest checkpoint."""
        return replace(self, checkpoint_ref=checkpoint_ref)

    def with_export(self, export_ref: str) -> ExecutionContext:
        """Return a copy with an export reference appended."""
        return replace(self, export_refs=(*self.export_refs, export_ref))

    def with_report(self, report_ref: str) -> ExecutionContext:
        """Return a copy with a report reference appended."""
        return replace(self, report_refs=(*self.report_refs, report_ref))

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation (excluding the token)."""
        return {
            "job_id": self.job_id,
            "correlation_id": self.correlation_id,
            "workflow_version": self.workflow_version,
            "target": self.target,
            "configuration_ref": self.configuration_ref,
            "adapter_name": self.adapter_name,
            "strategy": self.strategy.value if self.strategy else None,
            "dataset_ref": self.dataset_ref,
            "dataset_version": self.dataset_version,
            "checkpoint_ref": self.checkpoint_ref,
            "export_refs": list(self.export_refs),
            "report_refs": list(self.report_refs),
            "attributes": dict(self.attributes),
        }
