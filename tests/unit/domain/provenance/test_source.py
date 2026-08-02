"""Tests for provenance source references."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nexusai.domain.provenance import ArtifactReference, SourceReference


def _ref(**overrides: object) -> SourceReference:
    base: dict[str, object] = {
        "uri": "https://example.test/page",
        "retrieved_at": datetime(2026, 1, 1, tzinfo=UTC),
        "method": "http-get",
    }
    base.update(overrides)
    return SourceReference(**base)  # type: ignore[arg-type]


def test_source_reference_serialises() -> None:
    ref = _ref(content_hash="abc", attributes={"status": 200})
    assert ref.to_dict() == {
        "uri": "https://example.test/page",
        "retrieved_at": "2026-01-01T00:00:00+00:00",
        "method": "http-get",
        "content_hash": "abc",
        "attributes": {"status": 200},
    }


def test_source_reference_is_frozen() -> None:
    ref = _ref()
    with pytest.raises(AttributeError):
        ref.uri = "other"  # type: ignore[misc]


@pytest.mark.parametrize("field_name", ["uri", "method"])
def test_blank_required_fields_rejected(field_name: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        _ref(**{field_name: "   "})


def test_artifact_reference_serialises() -> None:
    ref = ArtifactReference(locator="s3://bucket/key", media_type="text/html", size_bytes=10)
    assert ref.to_dict() == {
        "locator": "s3://bucket/key",
        "media_type": "text/html",
        "description": "",
        "size_bytes": 10,
    }


def test_artifact_reference_rejects_blank_locator() -> None:
    with pytest.raises(ValueError, match="locator must not be empty"):
        ArtifactReference(locator=" ", media_type="text/html")
