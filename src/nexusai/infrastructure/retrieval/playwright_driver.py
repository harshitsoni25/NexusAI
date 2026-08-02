"""A Playwright-backed implementation of the browser driver seam.

This is the only module that imports Playwright, and it does so lazily inside
:meth:`start`, so importing the module -- for type checking, or to register the
provider -- never requires Playwright to be installed. Install it with the
``browser`` extra and run ``playwright install`` to use this driver in
production (ADR-0016).

Every Playwright call is wrapped so its exceptions surface as
:class:`BrowserError`, keeping the boundary translation that the rest of the
framework relies on.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from nexusai.domain.errors.exceptions import BrowserError
from nexusai.infrastructure.retrieval.browser import BrowserDriver, BrowserPage


class _PlaywrightPage:
    """Adapts a Playwright page to the :class:`BrowserPage` protocol."""

    def __init__(self, context: Any, page: Any) -> None:
        self._context = context
        self._page = page
        self._requests: list[Mapping[str, object]] = []
        # Record each completed response so captured_requests can report the
        # page's own network activity. Registered before navigation by new_page;
        # guarded so a page object without an event API never breaks construction.
        on = getattr(page, "on", None)
        if callable(on):
            on("response", self._record_response)

    def _record_response(self, response: Any) -> None:
        try:
            request = response.request
            self._requests.append(
                {
                    "url": str(response.url),
                    "method": str(request.method),
                    "status": int(response.status),
                    "type": str(getattr(request, "resource_type", "other")),
                    "size_bytes": 0,
                    "duration_ms": 0.0,
                }
            )
        except Exception:  # noqa: BLE001 - observation must never break retrieval
            return

    def goto(self, url: str, timeout_seconds: float | None) -> int:
        timeout_ms = None if timeout_seconds is None else timeout_seconds * 1000
        response = self._page.goto(url, timeout=timeout_ms)
        return int(response.status) if response is not None else 0

    def wait_for_selector(self, selector: str, timeout_seconds: float | None) -> None:
        timeout_ms = None if timeout_seconds is None else timeout_seconds * 1000
        self._page.wait_for_selector(selector, timeout=timeout_ms)

    def wait(self, seconds: float) -> None:
        self._page.wait_for_timeout(seconds * 1000)

    def perform(self, action: Mapping[str, object]) -> None:
        kind = action.get("type")
        if kind == "click" and isinstance(action.get("selector"), str):
            selector = str(action["selector"])
            timeout_ms = self._click_timeout_ms(action.get("timeout_seconds"))
            try:
                self._page.click(selector, timeout=timeout_ms)
            except Exception as exc:
                # A non-actionable target (hidden/disabled) makes Playwright's click
                # auto-wait until this timeout, then raise. Surface it through the
                # framework's error type rather than letting it escape or hang.
                raise BrowserError(
                    "Browser click failed", selector=selector, detail=str(exc)
                ) from exc
        elif kind == "scroll":
            raw_pixels = action.get("pixels", 2000)
            pixels = int(raw_pixels) if isinstance(raw_pixels, (int, float, str)) else 2000
            self._page.mouse.wheel(0, pixels)
        else:
            raise BrowserError("Unsupported browser action", action=dict(action))

    @staticmethod
    def _click_timeout_ms(timeout_seconds: object) -> float | None:
        """Convert a click timeout in seconds to Playwright milliseconds."""
        if timeout_seconds is None:
            return None
        if isinstance(timeout_seconds, (int, float)):
            return float(timeout_seconds) * 1000
        return None

    def content(self) -> str:
        return str(self._page.content())

    def current_url(self) -> str:
        return str(self._page.url)

    def screenshot(self, *, full_page: bool) -> bytes:
        return bytes(self._page.screenshot(full_page=full_page))

    def captured_requests(self) -> Sequence[Mapping[str, object]]:
        return tuple(self._requests)

    def close(self) -> None:
        self._page.close()
        self._context.close()


class PlaywrightBrowserDriver:
    """Launches Chromium through Playwright's synchronous API."""

    def __init__(self, *, headless: bool = True) -> None:
        self._headless = headless
        self._playwright: Any = None
        self._browser: Any = None

    def start(self) -> None:
        """Launch Chromium, importing Playwright lazily.

        Raises:
            BrowserError: If Playwright is not installed or the browser cannot be
                launched.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise BrowserError(
                "Playwright is not installed; install the 'browser' extra",
                detail=str(exc),
            ) from exc
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self._headless)
        except Exception as exc:  # pragma: no cover - requires a real browser
            raise BrowserError("Failed to launch the browser", detail=str(exc)) from exc

    def stop(self) -> None:
        """Close the browser and stop Playwright."""
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def new_page(self) -> BrowserPage:
        """Open a new page in a fresh, isolated context."""
        if self._browser is None:
            raise BrowserError("Browser driver used before start()")
        context = self._browser.new_context()
        page = context.new_page()
        return _PlaywrightPage(context, page)


_: BrowserDriver = PlaywrightBrowserDriver()
"""A module-level conformance check that the adapter satisfies the seam."""
