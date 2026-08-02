"""The unified document model and the request that produces it.

Every retrieval provider -- HTTP, browser, API -- returns the same
:class:`Document`, regardless of how it obtained the bytes. That uniformity is the
point of this phase: parsing and extraction operate on one abstraction and never
learn which provider produced it, so a parser written against an HTTP response
works unchanged on a browser-rendered page.

A :class:`RetrievalRequest` is likewise provider-neutral. It describes *what* to
retrieve and *how much* processing to ask for (render JavaScript, capture a
screenshot), never *which library* does it. A provider reads the directives it
understands and ignores the rest.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from nexusai.domain.model.network import NetworkObservation
from nexusai.domain.provenance.source import ArtifactReference, SourceReference
from nexusai.shared.types import JsonMapping


class RetrievalMethod(Enum):
    """How a request should be retrieved.

    A hint, not a binding: the retrieval engine maps a method to a provider that
    supports it. ``AUTO`` lets the engine choose, which is the common case -- most
    callers care about the URL, not the transport.
    """

    AUTO = "auto"
    HTTP = "http"
    BROWSER = "browser"
    API = "api"


class HttpVerb(Enum):
    """The HTTP verb for a request."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"


@dataclass(frozen=True, slots=True, kw_only=True)
class BrowserDirectives:
    """Options a browser provider honours; other providers ignore them.

    Kept as a separate object rather than loose fields on the request so that the
    request stays legible for the common HTTP case, where none of this applies.

    Attributes:
        render: Wait for the page to render before capturing content.
        wait_for_selector: A selector to wait for before the page is considered
            ready, for content injected after load.
        wait_for_timeout_seconds: A fixed settle delay, as a coarser alternative
            to waiting on a selector.
        capture_screenshot: Capture a screenshot artefact of the rendered page.
        full_page_screenshot: Capture the full scrollable page rather than the
            viewport.
        actions: An ordered sequence of interaction directives (click, scroll)
            applied before content capture, named by convention the provider
            understands.
    """

    render: bool = True
    wait_for_selector: str | None = None
    wait_for_timeout_seconds: float | None = None
    capture_screenshot: bool = False
    full_page_screenshot: bool = False
    actions: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    lazy_load: bool = False
    lazy_load_max_rounds: int = 10
    staged_screenshots: bool = False
    observe_network: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "actions", tuple(dict(action) for action in self.actions))


@dataclass(frozen=True, slots=True, kw_only=True)
class RetrievalRequest:
    """A provider-neutral description of a resource to retrieve.

    Attributes:
        url: The resource to retrieve.
        method: Which kind of provider should handle it.
        verb: The HTTP verb, for HTTP and API providers.
        headers: Request headers to send.
        params: Query-string parameters.
        body: A request body for non-GET verbs, as JSON-safe data.
        timeout_seconds: Per-request timeout override.
        browser: Directives honoured only by a browser provider.
        download: Treat the response as a downloadable artefact rather than a
            document to parse.
        labels: Free-form caller annotations, carried through onto the document's
            provenance for later correlation.
    """

    url: str
    method: RetrievalMethod = RetrievalMethod.AUTO
    verb: HttpVerb = HttpVerb.GET
    headers: Mapping[str, str] = field(default_factory=dict)
    params: Mapping[str, str] = field(default_factory=dict)
    body: JsonMapping | None = None
    timeout_seconds: float | None = None
    browser: BrowserDirectives | None = None
    download: bool = False
    labels: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.url.strip():
            raise ValueError("RetrievalRequest.url must not be empty")
        object.__setattr__(self, "headers", dict(self.headers))
        object.__setattr__(self, "params", dict(self.params))
        object.__setattr__(self, "labels", dict(self.labels))

    def for_url(self, url: str) -> RetrievalRequest:
        """Return a copy targeting ``url``, preserving all other settings.

        Used by pagination to derive the next request from the current one
        without restating its headers, verb and directives.
        """
        return replace_request(self, url=url)

    def with_params(self, **params: str) -> RetrievalRequest:
        """Return a copy with ``params`` merged over the existing ones."""
        return replace_request(self, params={**self.params, **params})


def replace_request(request: RetrievalRequest, **changes: Any) -> RetrievalRequest:
    """Return a copy of ``request`` with ``changes`` applied.

    A module-level helper rather than ``dataclasses.replace`` so that the
    post-init copying of mutable fields runs on the derived request too.
    """
    current: dict[str, Any] = {
        "url": request.url,
        "method": request.method,
        "verb": request.verb,
        "headers": dict(request.headers),
        "params": dict(request.params),
        "body": request.body,
        "timeout_seconds": request.timeout_seconds,
        "browser": request.browser,
        "download": request.download,
        "labels": dict(request.labels),
    }
    current.update(changes)
    return RetrievalRequest(**current)


@dataclass(frozen=True, slots=True, kw_only=True)
class Document:
    """The unified result of retrieving a resource.

    Provider-independent by construction: an HTTP response, a rendered page and
    an API payload all arrive as this shape. Extraction operates only on this
    abstraction, so it never depends on how the bytes were obtained.

    Attributes:
        url: The final URL after any redirects.
        content: The raw response body as bytes. Bytes rather than text because
            the correct decoding depends on headers and content, which is decided
            once, here, via :meth:`text`.
        status_code: The HTTP status, or a synthetic value for non-HTTP providers.
        headers: Response headers, with case-insensitive lookup via :meth:`header`.
        media_type: The parsed MIME type, without parameters (``text/html``).
        encoding: The character encoding, when known.
        retrieved_at: When retrieval completed, in UTC.
        provider: The name of the provider that produced this document.
        elapsed_seconds: How long retrieval took.
        metadata: Provider-specific response detail (redirect chain, timings).
        screenshot: A reference to a captured screenshot artefact, if any.
        downloads: References to downloaded artefacts associated with the request.
        source: The provenance root for this document.
    """

    url: str
    content: bytes
    status_code: int
    provider: str
    retrieved_at: datetime
    media_type: str = "application/octet-stream"
    encoding: str | None = None
    elapsed_seconds: float | None = None
    headers: Mapping[str, str] = field(default_factory=dict)
    metadata: JsonMapping = field(default_factory=dict)
    screenshot: ArtifactReference | None = None
    screenshots: Sequence[ArtifactReference] = field(default_factory=tuple)
    network: NetworkObservation | None = None
    downloads: Sequence[ArtifactReference] = field(default_factory=tuple)
    source: SourceReference | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", dict(self.headers))
        object.__setattr__(self, "metadata", dict(self.metadata))
        object.__setattr__(self, "downloads", tuple(self.downloads))

    def header(self, name: str, default: str | None = None) -> str | None:
        """Return a response header by case-insensitive name."""
        lowered = name.lower()
        for key, value in self.headers.items():
            if key.lower() == lowered:
                return value
        return default

    def text(self) -> str:
        """Decode the content to text using the known or a fallback encoding.

        Falls back to UTF-8 with replacement rather than raising, because a
        single undecodable byte should not lose an otherwise usable document; the
        replacement is visible and localised.
        """
        encoding = self.encoding or "utf-8"
        try:
            return self.content.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            return self.content.decode("utf-8", errors="replace")

    @property
    def is_success(self) -> bool:
        """Whether the status code is in the 2xx range."""
        return 200 <= self.status_code < 300

    @property
    def size_bytes(self) -> int:
        """The size of the raw content in bytes."""
        return len(self.content)

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable summary, excluding the raw bytes."""
        return {
            "url": self.url,
            "status_code": self.status_code,
            "provider": self.provider,
            "media_type": self.media_type,
            "encoding": self.encoding,
            "retrieved_at": self.retrieved_at.isoformat(),
            "elapsed_seconds": self.elapsed_seconds,
            "size_bytes": self.size_bytes,
            "screenshot": self.screenshot.to_dict() if self.screenshot else None,
            "screenshots": [ref.to_dict() for ref in self.screenshots],
            "network": self.network.to_dict() if self.network else None,
            "downloads": [ref.to_dict() for ref in self.downloads],
            "source": self.source.to_dict() if self.source else None,
        }
