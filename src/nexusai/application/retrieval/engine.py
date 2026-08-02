"""The retrieval engine: provider selection, recovery, pagination.

The engine is the orchestration layer of this phase. It holds a set of
providers and asks each whether it supports a request, delegating the transport
entirely; it consults a recovery policy on failure and enacts the policy's
decision -- sleeping before a retry, skipping, aborting -- so timing and effects
live in one place; and it drives a pagination strategy across pages. It never
opens a socket, parses a document or extracts a field. Those responsibilities
belong to providers, parsers and extractors respectively, and keeping them out of
the engine is what lets each be swapped without the engine changing.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from nexusai.domain.errors.exceptions import AcquisitionError, ConfigurationError
from nexusai.domain.model.recovery import RecoveryAction
from nexusai.domain.model.retrieval import Document, RetrievalRequest
from nexusai.domain.ports.retrieval import (
    PaginationStrategy,
    RecoveryPolicy,
    RetrievalProvider,
)

Sleeper = Callable[[float], None]
"""Blocks for a number of seconds; injected so tests need not really wait."""


@dataclass(frozen=True, slots=True, kw_only=True)
class RetrievalOutcome:
    """The result of a paginated retrieval.

    Attributes:
        documents: The documents retrieved, in page order.
        skipped: Requests whose retrieval was skipped by the recovery policy, with
            the reason, so a run can report what it did not obtain.
        aborted: Whether retrieval stopped early on an abort decision.
    """

    documents: Sequence[Document] = field(default_factory=tuple)
    skipped: Sequence[tuple[str, str]] = field(default_factory=tuple)
    aborted: bool = False

    @property
    def is_complete(self) -> bool:
        """Whether retrieval finished without an abort or any skips."""
        return not self.aborted and not self.skipped


class RetrievalEngine:
    """Coordinates retrieval across providers, recovery and pagination."""

    def __init__(
        self,
        providers: Sequence[RetrievalProvider],
        recovery: RecoveryPolicy,
        *,
        sleeper: Sleeper | None = None,
    ) -> None:
        if not providers:
            raise ConfigurationError("RetrievalEngine requires at least one provider")
        self._providers = tuple(providers)
        self._recovery = recovery
        self._sleep: Sleeper = sleeper or _no_sleep

    def retrieve(self, request: RetrievalRequest) -> Document:
        """Retrieve a single request, applying the recovery policy.

        Raises:
            AcquisitionError: If retrieval fails and the policy's decision is to
                abort, or the failure exhausts retries with an abort exhaustion
                action.
        """
        document = self._retrieve_with_recovery(request)
        if document is None:
            raise AcquisitionError("Retrieval failed and was not recoverable", url=request.url)
        return document

    def retrieve_paginated(
        self, request: RetrievalRequest, strategy: PaginationStrategy
    ) -> RetrievalOutcome:
        """Retrieve ``request`` and follow ``strategy`` across subsequent pages."""
        documents: list[Document] = []
        skipped: list[tuple[str, str]] = []
        current: RetrievalRequest | None = request
        while current is not None:
            try:
                document = self._retrieve_with_recovery(current, skipped)
            except _Aborted:
                return RetrievalOutcome(
                    documents=tuple(documents), skipped=tuple(skipped), aborted=True
                )
            if document is None:
                break
            documents.append(document)
            current = strategy.next_request(current, document)
        return RetrievalOutcome(documents=tuple(documents), skipped=tuple(skipped))

    def _retrieve_with_recovery(
        self, request: RetrievalRequest, skipped: list[tuple[str, str]] | None = None
    ) -> Document | None:
        """Attempt retrieval, applying recovery decisions until resolved.

        Returns the document on success, ``None`` if the policy skips the request,
        and raises :class:`_Aborted` if the policy aborts.
        """
        provider = self._select(request)
        attempt = 1
        while True:
            try:
                return provider.retrieve(request)
            except AcquisitionError as error:
                decision = self._recovery.decide(error, attempt)
                if decision.action is RecoveryAction.RETRY:
                    self._sleep(decision.delay_seconds)
                    attempt += 1
                    continue
                if decision.action is RecoveryAction.ABORT:
                    raise _Aborted(decision.reason) from error
                if decision.action is RecoveryAction.SKIP:
                    if skipped is not None:
                        skipped.append((request.url, decision.reason))
                    return None
                return None  # PARTIAL: yield nothing for this item, keep going

    def _select(self, request: RetrievalRequest) -> RetrievalProvider:
        for provider in self._providers:
            if provider.supports(request):
                return provider
        raise ConfigurationError(
            "No provider supports the request",
            url=request.url,
            method=request.method.value,
        )


class _Aborted(Exception):  # noqa: N818 - a control-flow signal, not a surfaced error
    """Internal signal that a recovery policy chose to abort the run."""


def _no_sleep(seconds: float) -> None:  # noqa: ARG001 - a no-op by design
    """A sleeper that returns immediately; the default for tests and dry runs."""
    return
