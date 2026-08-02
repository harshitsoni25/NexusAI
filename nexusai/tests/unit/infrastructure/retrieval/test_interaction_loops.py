"""Bounded scroll and Load-More loops verified with a deterministic fake page."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from nexusai.infrastructure.retrieval.interaction import (
    click_until_gone,
    scroll_until_stable,
)


class FakePage:
    """A fake page that reveals a fixed number of items over scroll rounds."""

    def __init__(self, *, growth_per_scroll: int, max_items: int) -> None:
        self.items = 0
        self._growth = growth_per_scroll
        self._max = max_items
        self.scrolls = 0
        self.clicks = 0

    def goto(self, url: str, timeout_seconds: float | None) -> int:
        return 200

    def wait_for_selector(self, selector: str, timeout_seconds: float | None) -> None:
        pass

    def wait(self, seconds: float) -> None:
        pass

    def perform(self, action: Mapping[str, object]) -> None:
        if action.get("type") == "scroll":
            self.scrolls += 1
            self.items = min(self._max, self.items + self._growth)
        elif action.get("type") == "click":
            self.clicks += 1
            self.items = min(self._max, self.items + self._growth)

    def content(self) -> str:
        return "x" * self.items

    def current_url(self) -> str:
        return "https://mock.local/"

    def screenshot(self, *, full_page: bool) -> bytes:
        return b""

    def captured_requests(self) -> Sequence[Mapping[str, object]]:
        return ()

    def close(self) -> None:
        pass


class TestScrollUntilStable:
    def test_stops_when_content_stops_growing(self) -> None:
        page = FakePage(growth_per_scroll=10, max_items=30)
        outcome = scroll_until_stable(
            page, lambda p: len(p.content()), max_rounds=20, no_progress_limit=2
        )
        assert outcome.final_measure == 30
        assert outcome.stopped_reason == "progress-stalled"
        assert outcome.rounds < 20  # terminated early

    def test_respects_max_rounds_bound(self) -> None:
        page = FakePage(growth_per_scroll=1, max_items=10_000)  # never stalls
        outcome = scroll_until_stable(
            page, lambda p: len(p.content()), max_rounds=5, no_progress_limit=2
        )
        assert outcome.rounds == 5
        assert outcome.stopped_reason == "max-rounds"

    def test_cancellation_stops_the_loop(self) -> None:
        page = FakePage(growth_per_scroll=10, max_items=10_000)
        outcome = scroll_until_stable(
            page, lambda p: len(p.content()), max_rounds=100, is_cancelled=lambda: True
        )
        assert outcome.stopped_reason == "cancelled"
        assert outcome.rounds == 0

    def test_never_runs_unbounded(self) -> None:
        page = FakePage(growth_per_scroll=5, max_items=10_000_000)
        outcome = scroll_until_stable(page, lambda p: len(p.content()), max_rounds=50)
        assert outcome.rounds <= 50


class TestClickUntilGone:
    def test_clicks_until_element_absent(self) -> None:
        page = FakePage(growth_per_scroll=5, max_items=15)
        outcome = click_until_gone(page, ".more", lambda p: len(p.content()) < 15, max_clicks=20)
        assert outcome.stopped_reason == "element-gone"
        assert page.items == 15

    def test_respects_max_clicks(self) -> None:
        page = FakePage(growth_per_scroll=1, max_items=10_000)
        outcome = click_until_gone(page, ".more", lambda p: True, max_clicks=3)
        assert outcome.rounds == 3
        assert outcome.stopped_reason == "max-rounds"
