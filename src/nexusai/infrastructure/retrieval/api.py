"""API retrieval provider for public REST and GraphQL endpoints.

A thin specialisation of the HTTP provider: it reuses the same pooled client and
document assembly, and adds only what an API call needs over a page fetch -- a
JSON ``Accept`` header by default, and a helper for wrapping a GraphQL query into
the standard POST body. It handles ``RetrievalMethod.API`` requests, leaving
``AUTO`` and ``HTTP`` to the HTTP provider so the two never contend.
"""

from __future__ import annotations

from collections.abc import Mapping

from nexusai.domain.model.retrieval import (
    Document,
    HttpVerb,
    RetrievalMethod,
    RetrievalRequest,
)
from nexusai.domain.ports.observability import Clock
from nexusai.infrastructure.retrieval.http import ClientFactory, HttpProvider
from nexusai.shared.types import JsonMapping, JsonValue


class ApiProvider:
    """Retrieves JSON from public REST and GraphQL endpoints."""

    name = "api"

    def __init__(
        self,
        clock: Clock,
        *,
        client_factory: ClientFactory | None = None,
        default_timeout_seconds: float = 30.0,
    ) -> None:
        self._http = HttpProvider(
            clock,
            client_factory=client_factory,
            default_timeout_seconds=default_timeout_seconds,
        )

    def supports(self, request: RetrievalRequest) -> bool:
        """Handle only requests explicitly marked as API retrieval."""
        return request.method is RetrievalMethod.API

    def initialize(self) -> None:
        """Open the underlying HTTP session."""
        self._http.initialize()

    def dispose(self) -> None:
        """Close the underlying HTTP session."""
        self._http.dispose()

    def retrieve(self, request: RetrievalRequest) -> Document:
        """Retrieve an API resource, defaulting to a JSON ``Accept`` header."""
        headers = {"accept": "application/json", **dict(request.headers)}
        prepared = request.for_url(request.url)
        prepared = _with_headers(prepared, headers)
        document = self._http.retrieve(prepared)
        return _relabel(document)

    @staticmethod
    def graphql_request(
        url: str, query: str, *, variables: JsonMapping | None = None
    ) -> RetrievalRequest:
        """Build a POST request carrying a GraphQL query in the standard shape."""
        body: dict[str, JsonValue] = {"query": query}
        if variables is not None:
            body["variables"] = dict(variables)
        return RetrievalRequest(
            url=url,
            method=RetrievalMethod.API,
            verb=HttpVerb.POST,
            headers={"content-type": "application/json"},
            body=body,
        )


def _with_headers(request: RetrievalRequest, headers: Mapping[str, str]) -> RetrievalRequest:
    from nexusai.domain.model.retrieval import replace_request

    return replace_request(request, headers=dict(headers))


def _relabel(document: Document) -> Document:
    from dataclasses import replace

    return replace(document, provider=ApiProvider.name)
