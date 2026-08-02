"""Tests for the HTTP and API providers, driven by a mock transport."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from nexusai.domain.errors.exceptions import (
    HttpStatusError,
    NetworkError,
    TimeoutError,  # noqa: A004 - the framework's TimeoutError, under test
)
from nexusai.domain.model.retrieval import HttpVerb, RetrievalMethod, RetrievalRequest
from nexusai.infrastructure.retrieval.api import ApiProvider
from nexusai.infrastructure.retrieval.http import HttpProvider
from nexusai.testing import SteppingClock


def _factory(
    handler: Callable[[httpx.Request], httpx.Response],
) -> Callable[[], httpx.Client]:
    def build() -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)

    return build


def test_http_provider_builds_document_with_provenance() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            content=b"<html>ok</html>",
        )

    provider = HttpProvider(SteppingClock(), client_factory=_factory(handler))
    provider.initialize()
    document = provider.retrieve(RetrievalRequest(url="https://example.com"))
    assert document.status_code == 200
    assert document.media_type == "text/html"
    assert document.encoding == "utf-8"
    assert document.provider == "http"
    assert document.source is not None
    assert document.source.content_hash
    assert document.elapsed_seconds is not None
    provider.dispose()


def test_http_provider_supports_auto_and_http_only() -> None:
    provider = HttpProvider(SteppingClock())
    assert provider.supports(RetrievalRequest(url="https://x")) is True
    assert (
        provider.supports(RetrievalRequest(url="https://x", method=RetrievalMethod.BROWSER))
        is False
    )


def test_http_provider_translates_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("slow", request=request)

    provider = HttpProvider(SteppingClock(), client_factory=_factory(handler))
    provider.initialize()
    with pytest.raises(TimeoutError):
        provider.retrieve(RetrievalRequest(url="https://x"))


def test_http_provider_translates_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    provider = HttpProvider(SteppingClock(), client_factory=_factory(handler))
    provider.initialize()
    with pytest.raises(NetworkError):
        provider.retrieve(RetrievalRequest(url="https://x"))


def test_http_provider_can_raise_on_error_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, content=b"down")

    provider = HttpProvider(
        SteppingClock(),
        client_factory=_factory(handler),
        raise_on_error_status=True,
    )
    provider.initialize()
    with pytest.raises(HttpStatusError) as caught:
        provider.retrieve(RetrievalRequest(url="https://x"))
    assert caught.value.retryable is True


def test_http_provider_reports_error_status_by_default() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, content=b"missing")

    provider = HttpProvider(SteppingClock(), client_factory=_factory(handler))
    provider.initialize()
    document = provider.retrieve(RetrievalRequest(url="https://x"))
    assert document.status_code == 404


def test_http_provider_raises_if_used_before_initialize() -> None:
    provider = HttpProvider(SteppingClock())
    with pytest.raises(NetworkError, match="before initialisation"):
        provider.retrieve(RetrievalRequest(url="https://x"))


def test_http_provider_sends_json_body_for_post() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["content"] = request.content
        return httpx.Response(200, content=b"{}")

    provider = HttpProvider(SteppingClock(), client_factory=_factory(handler))
    provider.initialize()
    provider.retrieve(RetrievalRequest(url="https://x", verb=HttpVerb.POST, body={"k": "v"}))
    assert b'"k"' in seen["content"]  # type: ignore[operator]


def test_api_provider_defaults_json_accept_and_relabels() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("accept") == "application/json"
        return httpx.Response(200, headers={"content-type": "application/json"}, content=b"{}")

    provider = ApiProvider(SteppingClock(), client_factory=_factory(handler))
    provider.initialize()
    document = provider.retrieve(RetrievalRequest(url="https://api", method=RetrievalMethod.API))
    assert document.provider == "api"
    provider.dispose()


def test_api_provider_supports_only_api_requests() -> None:
    provider = ApiProvider(SteppingClock())
    assert provider.supports(RetrievalRequest(url="https://x", method=RetrievalMethod.API)) is True
    assert provider.supports(RetrievalRequest(url="https://x")) is False


def test_api_provider_builds_graphql_request() -> None:
    request = ApiProvider.graphql_request("https://gql", "{ me }", variables={"id": 1})
    assert request.verb is HttpVerb.POST
    assert request.method is RetrievalMethod.API
    assert request.body == {"query": "{ me }", "variables": {"id": 1}}
