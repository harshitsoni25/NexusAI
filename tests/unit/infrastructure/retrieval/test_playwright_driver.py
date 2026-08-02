"""Tests for the Playwright adapter's pure translation logic.

The adapter is driven here with a fake underlying page object, so its mapping
from the browser seam onto Playwright calls is exercised without a real browser.
Launching an actual browser is out of scope and documented in ADR-0016; the
"Playwright not installed" path is covered because Playwright is genuinely absent
in this environment.
"""

from __future__ import annotations

from typing import Any

import pytest

from nexusai.domain.errors.exceptions import BrowserError
from nexusai.infrastructure.retrieval.playwright_driver import (
    PlaywrightBrowserDriver,
    _PlaywrightPage,
)


class _FakeResponse:
    status = 201


class _FakeMouse:
    def __init__(self) -> None:
        self.wheel_calls: list[tuple[int, int]] = []

    def wheel(self, dx: int, dy: int) -> None:
        self.wheel_calls.append((dx, dy))


class _FakePwPage:
    """A stand-in for a Playwright page, recording calls."""

    def __init__(self) -> None:
        self.url = "https://example.com/after"
        self.mouse = _FakeMouse()
        self.log: list[str] = []

    def goto(self, url: str, timeout: float | None) -> _FakeResponse:
        self.log.append(f"goto:{url}:{timeout}")
        return _FakeResponse()

    def wait_for_selector(self, selector: str, timeout: float | None) -> None:
        self.log.append(f"wait_selector:{selector}:{timeout}")

    def wait_for_timeout(self, ms: float) -> None:
        self.log.append(f"wait:{ms}")

    def click(self, selector: str, timeout: float | None = None) -> None:
        self.log.append(f"click:{selector}:{timeout}")

    def content(self) -> str:
        return "<html>pw</html>"

    def screenshot(self, *, full_page: bool) -> bytes:
        self.log.append(f"screenshot:{full_page}")
        return b"IMG"

    def close(self) -> None:
        self.log.append("close")


class _FakeContext:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _page() -> tuple[_PlaywrightPage, _FakePwPage, _FakeContext]:
    pw_page = _FakePwPage()
    context = _FakeContext()
    return _PlaywrightPage(context, pw_page), pw_page, context


def test_goto_converts_timeout_to_milliseconds_and_returns_status() -> None:
    page, pw_page, _ = _page()
    assert page.goto("https://x", 2.0) == 201
    assert pw_page.log[0] == "goto:https://x:2000.0"


def test_goto_with_no_response_returns_zero() -> None:
    class NoResponse(_FakePwPage):
        def goto(self, url: str, timeout: float | None) -> Any:
            return None

    page = _PlaywrightPage(_FakeContext(), NoResponse())
    assert page.goto("https://x", None) == 0


def test_wait_and_selector_and_content_and_url() -> None:
    page, pw_page, _ = _page()
    page.wait_for_selector("#a", None)
    page.wait(1.5)
    assert page.content() == "<html>pw</html>"
    assert page.current_url() == "https://example.com/after"
    assert "wait:1500.0" in pw_page.log


def test_perform_click_and_scroll_and_reject_unknown() -> None:
    page, pw_page, _ = _page()
    page.perform({"type": "click", "selector": "#btn"})
    page.perform({"type": "scroll", "pixels": 500})
    assert any(entry.startswith("click:#btn") for entry in pw_page.log)
    assert pw_page.mouse.wheel_calls == [(0, 500)]
    with pytest.raises(BrowserError, match="Unsupported browser action"):
        page.perform({"type": "teleport"})


def test_perform_click_passes_explicit_timeout_converted_to_milliseconds() -> None:
    page, pw_page, _ = _page()
    page.perform({"type": "click", "selector": "#btn", "timeout_seconds": 3})
    # 3 seconds must be handed to Playwright as 3000 milliseconds.
    assert "click:#btn:3000.0" in pw_page.log


def test_perform_click_without_timeout_passes_none() -> None:
    page, pw_page, _ = _page()
    page.perform({"type": "click", "selector": "#btn"})
    assert "click:#btn:None" in pw_page.log


def test_perform_click_surfaces_failure_as_browser_error() -> None:
    # A non-actionable target makes the real click time out and raise; the adapter
    # must surface that as a BrowserError rather than let it escape or hang.
    class _RaisingPage(_FakePwPage):
        def click(self, selector: str, timeout: float | None = None) -> None:
            raise TimeoutError("Timeout 5000ms exceeded waiting for actionability")

    page = _PlaywrightPage(_FakeContext(), _RaisingPage())
    with pytest.raises(BrowserError, match="Browser click failed"):
        page.perform({"type": "click", "selector": "#gone", "timeout_seconds": 5})


def test_screenshot_and_close_close_page_and_context() -> None:
    page, pw_page, context = _page()
    assert page.screenshot(full_page=True) == b"IMG"
    page.close()
    assert "close" in pw_page.log
    assert context.closed is True


def test_driver_start_raises_when_playwright_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Force the ImportError path deterministically, regardless of whether
    # Playwright is actually installed, so start() must translate it into a
    # BrowserError rather than crashing. Playwright is never uninstalled.
    import builtins

    real_import = builtins.__import__

    def blocked(name: str, *args: object, **kwargs: object) -> object:
        if name == "playwright" or name.startswith("playwright."):
            raise ImportError("No module named 'playwright' (simulated)")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", blocked)
    with pytest.raises(BrowserError, match="Playwright is not installed"):
        PlaywrightBrowserDriver().start()


def test_driver_new_page_before_start_raises() -> None:
    with pytest.raises(BrowserError, match="before start"):
        PlaywrightBrowserDriver().new_page()


def test_driver_stop_is_safe_when_never_started() -> None:
    PlaywrightBrowserDriver().stop()  # must not raise
