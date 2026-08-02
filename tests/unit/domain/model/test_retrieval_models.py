"""Tests for the unified document and retrieval request models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nexusai.domain.model.retrieval import (
    BrowserDirectives,
    Document,
    HttpVerb,
    RetrievalMethod,
    RetrievalRequest,
    replace_request,
)


def _doc(**overrides: object) -> Document:
    base: dict[str, object] = {
        "url": "https://example.com",
        "content": b"<html>caf\xc3\xa9</html>",
        "status_code": 200,
        "provider": "http",
        "retrieved_at": datetime(2026, 1, 1, tzinfo=UTC),
        "media_type": "text/html",
        "encoding": "utf-8",
    }
    base.update(overrides)
    return Document(**base)  # type: ignore[arg-type]


def test_request_rejects_empty_url() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        RetrievalRequest(url="  ")


def test_request_copies_mutable_fields() -> None:
    headers = {"a": "1"}
    request = RetrievalRequest(url="https://x", headers=headers)
    headers["a"] = "mutated"
    assert request.headers == {"a": "1"}


def test_for_url_and_with_params_preserve_other_settings() -> None:
    request = RetrievalRequest(url="https://x", verb=HttpVerb.POST, headers={"h": "v"})
    derived = request.for_url("https://y").with_params(page="2")
    assert derived.url == "https://y"
    assert derived.verb is HttpVerb.POST
    assert derived.headers == {"h": "v"}
    assert derived.params == {"page": "2"}


def test_replace_request_reapplies_copying() -> None:
    request = RetrievalRequest(url="https://x")
    changed = replace_request(request, params={"k": "v"})
    assert changed.params == {"k": "v"}
    assert request.params == {}


def test_browser_directives_copy_actions() -> None:
    actions = [{"type": "scroll"}]
    directives = BrowserDirectives(actions=actions)
    actions.append({"type": "click"})
    assert len(directives.actions) == 1


def test_document_text_decodes_with_declared_encoding() -> None:
    assert _doc().text() == "<html>café</html>"


def test_document_text_falls_back_on_bad_encoding() -> None:
    document = _doc(content=b"\xff\xfe", encoding="ascii")
    assert document.text()  # does not raise; replacement characters used


def test_document_header_lookup_is_case_insensitive() -> None:
    document = _doc(headers={"Content-Type": "text/html"})
    assert document.header("content-type") == "text/html"
    assert document.header("missing", "default") == "default"


def test_document_success_and_size() -> None:
    assert _doc().is_success is True
    assert _doc(status_code=404).is_success is False
    assert _doc(content=b"abc").size_bytes == 3


def test_document_to_dict_excludes_raw_bytes() -> None:
    payload = _doc().to_dict()
    assert "content" not in payload
    assert payload["status_code"] == 200
    assert payload["media_type"] == "text/html"


def test_request_method_default_is_auto() -> None:
    assert RetrievalRequest(url="https://x").method is RetrievalMethod.AUTO
