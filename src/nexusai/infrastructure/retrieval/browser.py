"""Browser retrieval provider driving a headless browser through a seam.

The provider owns the lifecycle -- browser, context, page -- and the navigation,
waiting, interaction and capture logic. It drives all of it through the
:class:`BrowserDriver` and :class:`BrowserPage` protocols rather than Playwright
directly, so the same logic is exercised in tests by a fake driver and in
production by the Playwright driver adapter (ADR-0016). Playwright is an optional
dependency; the seam is what keeps this module importable, type-checked and
tested without it installed.
"""

from __future__ import annotations

import contextlib
from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

from nexusai.domain.errors.exceptions import BrowserError
from nexusai.domain.model.network import NetworkObservation, summarise_requests
from nexusai.domain.model.retrieval import (
    BrowserDirectives,
    Document,
    RetrievalMethod,
    RetrievalRequest,
)
from nexusai.domain.ports.observability import Clock
from nexusai.domain.provenance.source import ArtifactReference
from nexusai.infrastructure.retrieval.artifacts import ArtifactWriter
from nexusai.infrastructure.retrieval.documents import build_document
from nexusai.infrastructure.retrieval.interaction import scroll_until_stable

# A framework-controlled ceiling for a single interaction (e.g. a Load-More click)
# when the request itself carries no timeout, so no interaction can block on a
# non-actionable element for longer than this. Used only as a fallback.
_DEFAULT_INTERACTION_TIMEOUT_SECONDS = 5.0


@runtime_checkable
class BrowserPage(Protocol):
    """A single browser page, driven through navigation and capture."""

    def goto(self, url: str, timeout_seconds: float | None) -> int:
        """Navigate to ``url`` and return the HTTP status of the main response."""
        ...

    def wait_for_selector(self, selector: str, timeout_seconds: float | None) -> None:
        """Block until an element matching ``selector`` is present."""
        ...

    def wait(self, seconds: float) -> None:
        """Block for a fixed settle delay."""
        ...

    def perform(self, action: Mapping[str, object]) -> None:
        """Apply one interaction directive, such as a click or a scroll."""
        ...

    def content(self) -> str:
        """Return the current rendered HTML."""
        ...

    def current_url(self) -> str:
        """Return the page's current URL after any client-side navigation."""
        ...

    def screenshot(self, *, full_page: bool) -> bytes:
        """Capture a screenshot of the page as PNG bytes."""
        ...

    def captured_requests(self) -> Sequence[Mapping[str, object]]:
        """Return the network requests observed during rendering.

        Each entry is a mapping with url, method, status, type, duration_ms and
        size_bytes keys. A driver that does not observe the network returns an
        empty sequence; the default implementation does so, so existing pages need
        not implement it.
        """
        return ()

    def close(self) -> None:
        """Close the page and release its resources."""
        ...


@runtime_checkable
class BrowserDriver(Protocol):
    """Launches and closes a browser and opens pages within it."""

    def start(self) -> None:
        """Launch the browser."""
        ...

    def stop(self) -> None:
        """Close the browser and all its contexts. Must not raise."""
        ...

    def new_page(self) -> BrowserPage:
        """Open a fresh page in a new context, isolated from other pages."""
        ...


class BrowserProvider:
    """Retrieves JavaScript-rendered pages through a browser driver."""

    name = "browser"

    def __init__(
        self,
        driver: BrowserDriver,
        clock: Clock,
        *,
        artifact_writer: ArtifactWriter | None = None,
    ) -> None:
        self._driver = driver
        self._clock = clock
        self._artifacts = artifact_writer
        self._started = False

    def supports(self, request: RetrievalRequest) -> bool:
        """Handle only requests explicitly routed to the browser."""
        return request.method is RetrievalMethod.BROWSER

    def initialize(self) -> None:
        """Launch the browser if it is not already running."""
        if not self._started:
            self._driver.start()
            self._started = True

    def dispose(self) -> None:
        """Stop the browser. Swallows driver errors so disposal never raises."""
        if self._started:
            with contextlib.suppress(Exception):  # disposal must never raise
                self._driver.stop()
            self._started = False

    def retrieve(self, request: RetrievalRequest) -> Document:
        """Render ``request`` in a fresh page and capture the result.

        Each retrieval uses a new page in its own context, so cookies and state do
        not leak between requests. The page is always closed, even on failure.

        Raises:
            BrowserError: On any driver-level failure during navigation or
                capture.
        """
        directives = request.browser or BrowserDirectives()
        started = self._clock.now()
        page = self._driver.new_page()
        staged: list[ArtifactReference] = []
        try:
            status = page.goto(request.url, request.timeout_seconds)
            self._capture_stage(page, directives, request.url, "initial", staged)
            self._apply_waits(page, directives)
            self._capture_stage(page, directives, request.url, "loaded", staged)
            if directives.lazy_load:
                self._apply_lazy_load(page, directives)
                self._capture_stage(page, directives, request.url, "scrolled", staged)
            self._apply_actions(page, directives.actions, request.timeout_seconds)
            html = page.content()
            final_url = page.current_url()
            self._capture_stage(page, directives, request.url, "post-extraction", staged)
            primary = self._capture_screenshot(page, directives, request.url)
            network = self._observe_network(page, directives)
        except BrowserError:
            raise
        except Exception as exc:
            raise BrowserError(
                "Browser retrieval failed", url=request.url, detail=str(exc)
            ) from exc
        finally:
            _close_quietly(page)

        finished = self._clock.now()
        return build_document(
            url=final_url,
            content=html.encode("utf-8"),
            status_code=status,
            provider=self.name,
            retrieved_at=started,
            headers={"content-type": "text/html; charset=utf-8"},
            method_label="browser",
            elapsed_seconds=(finished - started).total_seconds(),
            encoding_override="utf-8",
            metadata={"rendered": directives.render},
            screenshot=primary,
            screenshots=tuple(staged),
            network=network,
            source_attributes={"rendered": directives.render, "final_url": final_url},
        )

    def _apply_waits(self, page: BrowserPage, directives: BrowserDirectives) -> None:
        if directives.wait_for_selector:
            page.wait_for_selector(directives.wait_for_selector, None)
        if directives.wait_for_timeout_seconds:
            page.wait(directives.wait_for_timeout_seconds)

    def _apply_lazy_load(self, page: BrowserPage, directives: BrowserDirectives) -> None:
        """Trigger lazy-loaded content by scrolling until the page stops growing.

        Uses the bounded scroll loop so it always terminates, measuring progress by
        rendered-content length. A settle wait after each scroll gives lazily
        loaded resources a chance to arrive.
        """
        scroll_until_stable(
            page,
            lambda current: len(current.content()),
            max_rounds=directives.lazy_load_max_rounds,
            settle_seconds=directives.wait_for_timeout_seconds or 0.0,
        )

    def _apply_actions(
        self,
        page: BrowserPage,
        actions: Sequence[Mapping[str, object]],
        timeout_seconds: float | None,
    ) -> None:
        """Apply interaction directives with hard wall-clock and progress bounds.

        Click directives (the Load-More pattern) are the risk: a click on a control
        that has become hidden or disabled would otherwise auto-wait indefinitely.
        Each click carries an explicit timeout, so a non-actionable target raises
        rather than hangs; and the loop stops as soon as a click fails (the control
        is gone) or stops producing new content. Non-click directives (scroll) do
        not auto-wait and are applied directly.

        The rendered-content length is used as the progress signal rather than a
        DOM-presence check, because a control can remain in the DOM while being
        hidden or disabled -- DOM presence is not clickability.
        """
        interaction_timeout = (
            timeout_seconds if timeout_seconds is not None else _DEFAULT_INTERACTION_TIMEOUT_SECONDS
        )
        for action in actions:
            if action.get("type") != "click":
                page.perform(action)
                continue
            before = len(page.content())
            try:
                page.perform({**action, "timeout_seconds": interaction_timeout})
            except BrowserError:
                # The control is no longer actionable (hidden/disabled/removed):
                # the click timed out within the bound. Stop cleanly, keeping the
                # content gathered so far, rather than aborting the retrieval.
                break
            if len(page.content()) <= before:
                # The click produced no new content; there is nothing more to load.
                break

    def _observe_network(
        self, page: BrowserPage, directives: BrowserDirectives
    ) -> NetworkObservation | None:
        if not directives.observe_network:
            return None
        return summarise_requests(page.captured_requests())

    def _capture_stage(
        self,
        page: BrowserPage,
        directives: BrowserDirectives,
        url: str,
        stage: str,
        into: list[ArtifactReference],
    ) -> None:
        """Capture one lifecycle-stage screenshot, when staged capture is enabled."""
        if not directives.staged_screenshots or self._artifacts is None:
            return
        data = page.screenshot(full_page=directives.full_page_screenshot)
        name = f"screenshot-{stage}-{_safe_name(url)}.png"
        into.append(self._artifacts.write(name, data, "image/png"))

    def _capture_screenshot(
        self, page: BrowserPage, directives: BrowserDirectives, url: str
    ) -> ArtifactReference | None:
        if not directives.capture_screenshot or self._artifacts is None:
            return None
        data = page.screenshot(full_page=directives.full_page_screenshot)
        name = f"screenshot-{_safe_name(url)}.png"
        return self._artifacts.write(name, data, "image/png")


def _close_quietly(page: BrowserPage) -> None:
    # Closing a page must never mask the retrieval result or its failure.
    with contextlib.suppress(Exception):
        page.close()


def _safe_name(url: str) -> str:
    return "".join(character if character.isalnum() else "-" for character in url)[:80]
