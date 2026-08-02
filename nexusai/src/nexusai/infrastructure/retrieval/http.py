"""HTTP retrieval provider built on httpx.

Owns a reusable ``httpx.Client`` -- one connection pool, one cookie jar, one set
of default headers -- created on :meth:`initialize` and closed on
:meth:`dispose`. Reusing the client across requests is what gives connection
pooling and keep-alive; a fresh client per request would throw that away.

The httpx client is injectable through a factory so tests supply one backed by a
mock transport and exercise the whole provider with no network. Every httpx
exception is translated into the framework hierarchy here, at the boundary, so
nothing httpx-shaped reaches the engine.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

from nexusai.domain.errors.exceptions import (
    HttpStatusError,
    NetworkError,
    TimeoutError,  # noqa: A004 - the framework's TimeoutError, deliberately shadowing
)
from nexusai.domain.model.retrieval import Document, HttpVerb, RetrievalMethod, RetrievalRequest
from nexusai.domain.ports.observability import Clock
from nexusai.infrastructure.retrieval.documents import build_document

ClientFactory = Callable[[], httpx.Client]
"""A callable that builds the httpx client the provider will own."""


class HttpProvider:
    """Retrieves resources over HTTP with a pooled, cookie-aware session."""

    name = "http"

    def __init__(
        self,
        clock: Clock,
        *,
        client_factory: ClientFactory | None = None,
        default_timeout_seconds: float = 30.0,
        raise_on_error_status: bool = False,
    ) -> None:
        self._clock = clock
        self._factory = client_factory or _default_client_factory(default_timeout_seconds)
        self._default_timeout = default_timeout_seconds
        self._raise_on_error_status = raise_on_error_status
        self._client: httpx.Client | None = None

    def supports(self, request: RetrievalRequest) -> bool:
        """Handle AUTO and HTTP requests that are not download-only browser jobs."""
        return request.method in {RetrievalMethod.AUTO, RetrievalMethod.HTTP}

    def initialize(self) -> None:
        """Open the underlying httpx client if it is not already open."""
        if self._client is None:
            self._client = self._factory()

    def dispose(self) -> None:
        """Close the underlying httpx client. Safe to call more than once."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def retrieve(self, request: RetrievalRequest) -> Document:
        """Retrieve ``request`` over HTTP and return a unified document.

        Raises:
            TimeoutError: If the request exceeds its timeout.
            NetworkError: On any other transport-level failure.
            HttpStatusError: On a 4xx/5xx status when ``raise_on_error_status`` is
                set; otherwise the status is reported on the returned document.
        """
        client = self._require_client()
        started = self._clock.now()
        try:
            response = client.request(
                request.verb.value,
                request.url,
                headers=dict(request.headers),
                params=dict(request.params),
                json=_json_body(request),
                timeout=request.timeout_seconds or self._default_timeout,
            )
        except httpx.TimeoutException as exc:
            raise TimeoutError("HTTP request timed out", url=request.url) from exc
        except httpx.HTTPError as exc:
            raise NetworkError("HTTP request failed", url=request.url, detail=str(exc)) from exc

        finished = self._clock.now()
        if self._raise_on_error_status and response.status_code >= 400:
            raise HttpStatusError(
                "HTTP request returned an error status",
                status_code=response.status_code,
                url=request.url,
            )
        return build_document(
            url=str(response.url),
            content=response.content,
            status_code=response.status_code,
            provider=self.name,
            retrieved_at=started,
            headers=dict(response.headers.items()),
            method_label="http-get" if request.verb is HttpVerb.GET else "http",
            elapsed_seconds=(finished - started).total_seconds(),
            encoding_override=response.encoding,
            metadata={
                "redirects": [str(item.url) for item in response.history],
                "http_version": response.http_version,
            },
        )

    def _require_client(self) -> httpx.Client:
        if self._client is None:
            raise NetworkError("HTTP provider used before initialisation", url="")
        return self._client


def _json_body(request: RetrievalRequest) -> Any:
    if request.verb is HttpVerb.GET or request.body is None:
        return None
    return dict(request.body)


def _default_client_factory(timeout_seconds: float) -> ClientFactory:
    def factory() -> httpx.Client:
        return httpx.Client(
            follow_redirects=True,
            timeout=timeout_seconds,
            headers={"user-agent": "nexusai/0.1 (+public-data)"},
        )

    return factory
