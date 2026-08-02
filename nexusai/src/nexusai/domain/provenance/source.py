"""Source traceability value objects.

Provenance is a structural member of the record type rather than a side table
(ADR-0008), so a record without provenance is not representable. These are the
building blocks: where a value came from, and which artefact preserves the
evidence.

They are frozen and technology-agnostic. A ``SourceReference`` describes an
origin as a URI and a moment; it says nothing about HTTP, browsers or files,
because the same provenance model must serve a page fetched over HTTP, a row
read from an API and a record parsed from a downloaded document.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from nexusai.shared.types import JsonMapping


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceReference:
    """Where a piece of data came from.

    Attributes:
        uri: The canonical location of the source, as a string. A URI rather than
            a URL because the origin is not always web -- it may be a file or an
            API endpoint.
        retrieved_at: When the source was obtained, in UTC.
        method: How it was obtained, as a free-form label ("http-get",
            "browser", "api"). A label rather than an enum because the framework
            core must not enumerate acquisition technologies it knows nothing
            about; strategies supply their own.
        content_hash: Optional digest of the retrieved content, which is what
            lets change detection tell "genuinely different" from "fetched
            again".
        attributes: Additional origin detail a strategy chooses to record, such
            as a status code or a content type. Kept as an open mapping so the
            core need not know every strategy's vocabulary.
    """

    uri: str
    retrieved_at: datetime
    method: str
    content_hash: str | None = None
    attributes: JsonMapping = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.uri.strip():
            raise ValueError("SourceReference.uri must not be empty")
        if not self.method.strip():
            raise ValueError("SourceReference.method must not be empty")

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "uri": self.uri,
            "retrieved_at": self.retrieved_at.isoformat(),
            "method": self.method,
            "content_hash": self.content_hash,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactReference:
    """A pointer to a stored artefact that preserves evidence of a source.

    HTML snapshots, screenshots and diff images are written to the artefact store
    and referenced from provenance. The reference is a locator and a description,
    never the bytes: the domain records *that* an artefact exists and where,
    while the infrastructure owns its storage.

    Attributes:
        locator: An opaque handle the artefact store understands. Opaque so the
            domain need not know whether it is a path, a key or a URL.
        media_type: The artefact's media type, such as ``text/html``.
        description: Why this artefact was captured -- "rendered page", "initial
            load screenshot".
        size_bytes: Size when known, for reporting and retention decisions.
    """

    locator: str
    media_type: str
    description: str = ""
    size_bytes: int | None = None

    def __post_init__(self) -> None:
        if not self.locator.strip():
            raise ValueError("ArtifactReference.locator must not be empty")

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "locator": self.locator,
            "media_type": self.media_type,
            "description": self.description,
            "size_bytes": self.size_bytes,
        }
