"""Models for observing the network activity of a rendered page.

A JavaScript-rendered page issues its own requests -- XHR/fetch calls, GraphQL
queries, images, scripts -- that a plain HTTP fetch never sees. These models
describe what was observed, as pure values: one record per captured request, and a
summary that rolls them up by outcome and resource type. Capturing the requests is
the browser driver's job (it needs the live browser); interpreting and summarising
them is pure and lives here.

Only bounded, non-sensitive fields are modelled -- URL, method, status, resource
type, duration and size -- never request bodies or headers, which could carry
secrets.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import cast


class ResourceType(Enum):
    """The kind of resource a captured request fetched."""

    DOCUMENT = "document"
    XHR = "xhr"
    FETCH = "fetch"
    SCRIPT = "script"
    STYLESHEET = "stylesheet"
    IMAGE = "image"
    FONT = "font"
    MEDIA = "media"
    OTHER = "other"

    @classmethod
    def from_label(cls, label: str) -> ResourceType:
        """Map a driver's resource-type label to a known type, defaulting to OTHER."""
        try:
            return cls(label.lower())
        except ValueError:
            return cls.OTHER


@dataclass(frozen=True, slots=True, kw_only=True)
class CapturedRequest:
    """One network request observed while rendering a page.

    Attributes:
        url: The request URL.
        method: The HTTP method.
        status_code: The response status, or ``0`` if it never completed.
        resource_type: What kind of resource was fetched.
        duration_ms: How long the request took, in milliseconds.
        size_bytes: The response size in bytes, when known.
    """

    url: str
    method: str
    status_code: int
    resource_type: ResourceType
    duration_ms: float = 0.0
    size_bytes: int = 0

    @property
    def failed(self) -> bool:
        """Whether the request failed (no status, or a 4xx/5xx status)."""
        return self.status_code == 0 or self.status_code >= 400

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {
            "url": self.url,
            "method": self.method,
            "status_code": self.status_code,
            "resource_type": self.resource_type.value,
            "duration_ms": self.duration_ms,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class NetworkObservation:
    """A summary of the network activity observed for one page render.

    Attributes:
        requests: The captured requests.
        total_requests: How many requests were observed.
        failed_requests: How many failed.
        by_resource_type: Counts keyed by resource type.
        total_bytes: The sum of response sizes.
        api_requests: The XHR/fetch requests, which usually carry the real data.
    """

    requests: Sequence[CapturedRequest] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "requests", tuple(self.requests))

    @property
    def total_requests(self) -> int:
        """How many requests were observed."""
        return len(self.requests)

    @property
    def failed_requests(self) -> int:
        """How many observed requests failed."""
        return sum(1 for request in self.requests if request.failed)

    @property
    def total_bytes(self) -> int:
        """The total observed response size in bytes."""
        return sum(request.size_bytes for request in self.requests)

    @property
    def by_resource_type(self) -> dict[str, int]:
        """Request counts grouped by resource type."""
        counts: dict[str, int] = {}
        for request in self.requests:
            key = request.resource_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    @property
    def api_requests(self) -> tuple[CapturedRequest, ...]:
        """The XHR and fetch requests, which typically carry the page's data."""
        return tuple(
            request
            for request in self.requests
            if request.resource_type in {ResourceType.XHR, ResourceType.FETCH}
        )

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable summary."""
        return {
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "total_bytes": self.total_bytes,
            "by_resource_type": self.by_resource_type,
            "api_request_count": len(self.api_requests),
            "requests": [request.to_dict() for request in self.requests],
        }


def summarise_requests(
    raw: Sequence[Mapping[str, object]],
) -> NetworkObservation:
    """Build a :class:`NetworkObservation` from a driver's raw request dicts.

    Each raw entry is expected to carry url, method, status, type, duration and
    size keys; missing keys default safely so a partial capture never raises.
    """
    captured = [
        CapturedRequest(
            url=str(entry.get("url", "")),
            method=str(entry.get("method", "GET")),
            status_code=int(cast("int", entry.get("status", 0))),
            resource_type=ResourceType.from_label(str(entry.get("type", "other"))),
            duration_ms=float(cast("float", entry.get("duration_ms", 0.0))),
            size_bytes=int(cast("int", entry.get("size_bytes", 0))),
        )
        for entry in raw
    ]
    return NetworkObservation(requests=captured)
