"""Contracts for the retrieval subsystem.

A :class:`RetrievalProvider` obtains a resource and returns the unified
:class:`Document`; the retrieval engine selects among providers and never speaks
a transport itself. A :class:`PaginationStrategy` derives the next request from
the current document, keeping "how to page" out of the engine and in
interchangeable strategies. A :class:`RecoveryPolicy` turns a failure into a
decision.

All three are ``Protocol`` contracts (ADR-0003), so an infrastructure adapter
satisfies them structurally without importing the domain.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from nexusai.domain.model.recovery import RecoveryDecision
from nexusai.domain.model.retrieval import Document, RetrievalRequest


@runtime_checkable
class RetrievalProvider(Protocol):
    """Obtains a resource and returns a unified document.

    A provider owns one transport -- HTTP, browser, API -- and nothing else. It
    performs no parsing and no extraction: its sole output is bytes wrapped in a
    :class:`Document`. It is lifecycle-aware because a provider typically holds a
    reusable resource (a session, a browser) that must be opened before use and
    released after.
    """

    @property
    def name(self) -> str:
        """A stable identifier used to register and select the provider."""
        ...

    def supports(self, request: RetrievalRequest) -> bool:
        """Whether this provider can handle ``request``."""
        ...

    def retrieve(self, request: RetrievalRequest) -> Document:
        """Retrieve the resource described by ``request``.

        Raises:
            AcquisitionError: Or a subclass, on any transport-level failure. The
                provider translates library-specific exceptions into the
                framework hierarchy so recovery policies can reason about them.
        """
        ...

    def initialize(self) -> None:
        """Acquire the provider's reusable resource."""
        ...

    def dispose(self) -> None:
        """Release the provider's reusable resource. Must not raise."""
        ...


@runtime_checkable
class PaginationStrategy(Protocol):
    """Derives the next request in a sequence of pages.

    A strategy inspects the current request and the document it produced and
    returns the request for the next page, or ``None`` when the sequence is
    exhausted. It performs no retrieval of its own -- the engine drives the loop
    -- which is what keeps pagination interchangeable and testable without a
    network.
    """

    @property
    def name(self) -> str:
        """A stable identifier used to register and select the strategy."""
        ...

    def next_request(
        self, request: RetrievalRequest, document: Document
    ) -> RetrievalRequest | None:
        """Return the next request, or ``None`` if there are no more pages."""
        ...


@runtime_checkable
class RecoveryPolicy(Protocol):
    """Decides what to do when retrieval fails.

    Consulted by the engine with the raised error and the current attempt number.
    The policy returns a :class:`RecoveryDecision`; it never retries or sleeps
    itself, so it stays pure and the engine keeps control of timing and effects.
    """

    @property
    def name(self) -> str:
        """A stable identifier for the policy."""
        ...

    def decide(self, error: Exception, attempt: int) -> RecoveryDecision:
        """Return the decision for ``error`` on attempt ``attempt`` (1-based)."""
        ...
