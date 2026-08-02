"""Regression tests for bounded Load-More interaction (Phase 10R-CV R3).

A real-browser C1 run hung on Load More: the provider issued a fixed number of
clicks, and a click on a button that had become hidden/disabled auto-waited without
a framework timeout. These tests drive the provider with a deterministic fake page
that models a control which stops responding, proving the loop terminates cleanly on
control unavailability, on lack of progress, and within its round bound -- without a
real browser.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest

from nexusai.domain.errors.exceptions import BrowserError
from nexusai.domain.model.retrieval import (
    BrowserDirectives,
    RetrievalMethod,
    RetrievalRequest,
)
from nexusai.infrastructure.retrieval.browser import BrowserProvider
from nexusai.testing import FrozenClock

pytestmark = pytest.mark.component


class LoadMorePage:
    """A page whose Load-More control reveals items, then becomes unavailable.

    After ``cap`` items the control stops responding: a further click raises, the
    way a real click on a hidden/disabled button times out and surfaces as a
    ``BrowserError``.
    """

    def __init__(self, *, per_click: int = 2, start: int = 2, cap: int = 6) -> None:
        self.items = start
        self._per_click = per_click
        self._cap = cap
        self.click_attempts = 0

    def goto(self, url: str, timeout_seconds: float | None) -> int:
        return 200

    def wait_for_selector(self, selector: str, timeout_seconds: float | None) -> None:
        pass

    def wait(self, seconds: float) -> None:
        pass

    def perform(self, action: Mapping[str, object]) -> None:
        if action.get("type") != "click":
            return
        self.click_attempts += 1
        if self.items >= self._cap:
            # Control is gone; a real click would time out within the bound.
            raise BrowserError("Browser click failed", detail="timeout")
        self.items = min(self._cap, self.items + self._per_click)

    def content(self) -> str:
        items = "".join(f'<li class="item">{i}</li>' for i in range(self.items))
        return f"<html><body><ul>{items}</ul></body></html>"

    def current_url(self) -> str:
        return "https://mock.local/final"

    def screenshot(self, *, full_page: bool) -> bytes:
        return b""

    def captured_requests(self) -> Sequence[Mapping[str, object]]:
        return ()

    def close(self) -> None:
        pass


class AlwaysGrowsPage(LoadMorePage):
    """A control that always reveals more and never becomes unavailable."""

    def perform(self, action: Mapping[str, object]) -> None:
        if action.get("type") == "click":
            self.click_attempts += 1
            self.items += self._per_click  # unbounded growth; never raises


class _Driver:
    def __init__(self, page: LoadMorePage) -> None:
        self._page = page

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def new_page(self) -> LoadMorePage:
        return self._page


def _retrieve(page: LoadMorePage, *, clicks: int) -> str:
    provider = BrowserProvider(_Driver(page), FrozenClock())
    actions = [{"type": "click", "selector": "#more"} for _ in range(clicks)]
    request = RetrievalRequest(
        url="https://mock.local/load-more",
        method=RetrievalMethod.BROWSER,
        browser=BrowserDirectives(actions=actions),
    )
    return provider.retrieve(request).content.decode("utf-8")


class TestStopsWhenControlUnavailable:
    def test_realistic_case_six_items_then_clean_stop(self) -> None:
        # 3 clicks requested, but the control vanishes after the 6th item: the
        # provider must return 6 items and terminate cleanly (no hang, no raise).
        page = LoadMorePage(per_click=2, start=2, cap=6)
        html = _retrieve(page, clicks=3)
        assert html.count('class="item"') == 6

    def test_unavailable_control_does_not_abort_retrieval(self) -> None:
        page = LoadMorePage(per_click=2, start=2, cap=6)
        html = _retrieve(page, clicks=10)  # far more than needed
        assert html.count('class="item"') == 6  # still terminates at the cap


class TestMaxRoundsBoundedness:
    def test_never_exceeds_requested_click_count(self) -> None:
        # A control that always grows must still be bounded by the action count.
        page = AlwaysGrowsPage(per_click=1, start=0, cap=10_000)
        _retrieve(page, clicks=4)
        assert page.click_attempts == 4  # bounded by rounds, never unbounded

    def test_stops_early_when_no_progress(self) -> None:
        # A control present but producing nothing must not be clicked repeatedly.
        class InertPage(LoadMorePage):
            def perform(self, action: Mapping[str, object]) -> None:
                if action.get("type") == "click":
                    self.click_attempts += 1  # no content change

        page = InertPage(start=3, cap=3)
        _retrieve(page, clicks=5)
        assert page.click_attempts == 1  # stopped after the first no-progress click
