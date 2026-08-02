"""Tests for the shared document-assembly helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from nexusai.infrastructure.retrieval.documents import (
    build_document,
    content_hash,
    split_media_type,
)


def test_content_hash_is_stable() -> None:
    assert content_hash(b"abc") == content_hash(b"abc")
    assert content_hash(b"abc") != content_hash(b"abd")


def test_split_media_type_separates_charset() -> None:
    assert split_media_type("text/html; charset=utf-8") == ("text/html", "utf-8")
    assert split_media_type("application/json") == ("application/json", None)
    assert split_media_type(None) == ("application/octet-stream", None)
    assert split_media_type('text/html; charset="ISO-8859-1"') == ("text/html", "ISO-8859-1")


def test_build_document_attaches_provenance() -> None:
    document = build_document(
        url="https://x",
        content=b"<html>",
        status_code=200,
        provider="http",
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        headers={"Content-Type": "text/html; charset=utf-8"},
        method_label="http-get",
    )
    assert document.media_type == "text/html"
    assert document.encoding == "utf-8"
    assert document.source is not None
    assert document.source.method == "http-get"
    assert document.source.attributes["provider"] == "http"
    assert document.source.content_hash == content_hash(b"<html>")
