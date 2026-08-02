"""Tests for the browser provider, driven through a fake browser seam."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest

from nexusai.domain.errors.exceptions import BrowserError
from nexusai.domain.model.retrieval import (
    BrowserDirectives,
    RetrievalMethod,
    RetrievalRequest,
)
from nexusai.infrastructure.retrieval.artifacts import InMemoryArtifactWriter
from nexusai.infrastructure.retrieval.browser import BrowserPage, BrowserProvider
from nexusai.testing import SteppingClock


class FakePage:
    """A scripted page recording operations, implementing the browser seam."""

    def __init__(self, *, fail_on: str | None = None) -> None:
        self.fail_on = fail_on
        self.log: list[str] = []
        self.closed = False

    def goto(self, url: str, timeout_seconds: float | None) -> int:
        if self.fail_on == "goto":
            raise RuntimeError("navigation failed")
        self.log.append(f"goto:{url}")
        return 200

    def wait_for_selector(self, selector: str, timeout_seconds: float | None) -> None:
        self.log.append(f"wait_selector:{selector}")

    def wait(self, seconds: float) -> None:
        self.log.append(f"wait:{seconds}")

    def perform(self, action: Mapping[str, object]) -> None:
        self.log.append(f"perform:{action.get('type')}")

    def content(self) -> str:
        return "<html><body>rendered</body></html>"

    def current_url(self) -> str:
        return "https://example.com/final"

    def screenshot(self, *, full_page: bool) -> bytes:
        self.log.append(f"screenshot:{full_page}")
        return b"PNGDATA"

    def captured_requests(self) -> Sequence[Mapping[str, object]]:
        return ()

    def close(self) -> None:
        self.closed = True


class FakeDriver:
    """A driver returning a scripted page and tracking lifecycle."""

    def __init__(self, page: FakePage | None = None) -> None:
        self.page = page or FakePage()
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def new_page(self) -> BrowserPage:
        return self.page


def _browser_request(**browser: object) -> RetrievalRequest:
    return RetrievalRequest(
        url="https://example.com",
        method=RetrievalMethod.BROWSER,
        browser=BrowserDirectives(**browser),  # type: ignore[arg-type]
    )


def test_browser_provider_renders_and_captures() -> None:
    driver = FakeDriver()
    writer = InMemoryArtifactWriter()
    provider = BrowserProvider(driver, SteppingClock(), artifact_writer=writer)
    provider.initialize()
    assert driver.started is True
    document = provider.retrieve(
        _browser_request(
            wait_for_selector="#ready",
            wait_for_timeout_seconds=0.2,
            capture_screenshot=True,
            actions=[{"type": "scroll"}],
        )
    )
    assert document.url == "https://example.com/final"
    assert document.provider == "browser"
    assert document.text() == "<html><body>rendered</body></html>"
    assert document.screenshot is not None
    assert document.screenshot.locator.startswith("memory://")
    assert driver.page.log == [
        "goto:https://example.com",
        "wait_selector:#ready",
        "wait:0.2",
        "perform:scroll",
        "screenshot:False",
    ]
    assert driver.page.closed is True


def test_browser_provider_supports_only_browser_requests() -> None:
    provider = BrowserProvider(FakeDriver(), SteppingClock())
    assert provider.supports(_browser_request()) is True
    assert provider.supports(RetrievalRequest(url="https://x")) is False


def test_browser_provider_skips_screenshot_without_writer() -> None:
    provider = BrowserProvider(FakeDriver(), SteppingClock())
    provider.initialize()
    document = provider.retrieve(_browser_request(capture_screenshot=True))
    assert document.screenshot is None


def test_browser_provider_translates_failures_and_closes_page() -> None:
    page = FakePage(fail_on="goto")
    provider = BrowserProvider(FakeDriver(page), SteppingClock())
    provider.initialize()
    with pytest.raises(BrowserError):
        provider.retrieve(_browser_request())
    assert page.closed is True


def test_browser_provider_dispose_stops_driver_and_is_idempotent() -> None:
    driver = FakeDriver()
    provider = BrowserProvider(driver, SteppingClock())
    provider.initialize()
    provider.dispose()
    provider.dispose()
    assert driver.stopped is True


def test_browser_provider_dispose_swallows_driver_errors() -> None:
    class ExplodingDriver(FakeDriver):
        def stop(self) -> None:
            raise RuntimeError("cannot stop")

    provider = BrowserProvider(ExplodingDriver(), SteppingClock())
    provider.initialize()
    provider.dispose()  # must not raise
