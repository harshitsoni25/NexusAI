"""Helpers for assembling a unified document with provenance.

Every provider ends the same way: wrap bytes and response detail in a
:class:`Document`, attaching a :class:`SourceReference` so the document is
traceable from the moment it is created. Centralising that here keeps content
hashing and MIME parsing consistent across providers -- a screenshot-bearing
browser document and a plain HTTP one carry provenance in the identical shape.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from datetime import datetime

from nexusai.domain.model.network import NetworkObservation
from nexusai.domain.model.retrieval import Document
from nexusai.domain.provenance.source import ArtifactReference, SourceReference
from nexusai.shared.types import JsonMapping, JsonValue


def content_hash(content: bytes) -> str:
    """Return the SHA-256 hex digest of ``content``, for change detection."""
    return hashlib.sha256(content).hexdigest()


def split_media_type(raw: str | None) -> tuple[str, str | None]:
    """Split a Content-Type header into (media_type, charset).

    The media type is lower-cased and stripped of parameters; the charset is
    returned separately when present, so the document records a clean MIME type
    and a usable encoding rather than one tangled string.
    """
    if not raw:
        return "application/octet-stream", None
    parts = [segment.strip() for segment in raw.split(";")]
    media_type = parts[0].lower() or "application/octet-stream"
    charset: str | None = None
    for parameter in parts[1:]:
        key, _, value = parameter.partition("=")
        if key.strip().lower() == "charset" and value:
            charset = value.strip().strip('"') or None
    return media_type, charset


def build_document(
    *,
    url: str,
    content: bytes,
    status_code: int,
    provider: str,
    retrieved_at: datetime,
    headers: Mapping[str, str],
    method_label: str,
    elapsed_seconds: float | None = None,
    encoding_override: str | None = None,
    metadata: JsonMapping | None = None,
    screenshot: ArtifactReference | None = None,
    screenshots: Sequence[ArtifactReference] = (),
    network: NetworkObservation | None = None,
    source_attributes: Mapping[str, JsonValue] | None = None,
    downloads: Sequence[ArtifactReference] = (),
) -> Document:
    """Assemble a :class:`Document` with an attached provenance root."""
    media_type, charset = split_media_type(_lookup(headers, "content-type"))
    attributes: dict[str, JsonValue] = {"status_code": status_code, "provider": provider}
    if source_attributes:
        attributes.update(source_attributes)
    source = SourceReference(
        uri=url,
        retrieved_at=retrieved_at,
        method=method_label,
        content_hash=content_hash(content),
        attributes=attributes,
    )
    return Document(
        url=url,
        content=content,
        status_code=status_code,
        provider=provider,
        retrieved_at=retrieved_at,
        media_type=media_type,
        encoding=encoding_override or charset,
        elapsed_seconds=elapsed_seconds,
        headers=dict(headers),
        metadata=dict(metadata or {}),
        screenshot=screenshot,
        screenshots=tuple(screenshots),
        network=network,
        downloads=tuple(downloads),
        source=source,
    )


def _lookup(headers: Mapping[str, str], name: str) -> str | None:
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return None
