"""Bounded page-interaction loops: infinite scroll and Load More.

Driving a page that reveals content on scroll or on a "load more" click needs a
loop, and a loop against a live page needs hard bounds or it can run forever. This
module provides those loops as pure control flow over a minimal page protocol,
with progress measured through an injected callback rather than any site-specific
condition, so the core never hardcodes a selector or a button label.

Every loop terminates: it stops when progress stalls for a configured number of
rounds, when a maximum number of rounds is reached, or when the caller cancels.
The interaction directives themselves are applied through the same ``perform``
mechanism the browser provider already uses, so this adds control flow, not a new
way to touch the page.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol


class _Scrollable(Protocol):
    """The minimal page surface the interaction loops need.

    Declared locally so this module depends on no browser class, keeping the
    dependency graph acyclic; the concrete ``BrowserPage`` satisfies it
    structurally.
    """

    def perform(self, action: Mapping[str, object]) -> None: ...

    def wait(self, seconds: float) -> None: ...

    def content(self) -> str: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class ScrollOutcome:
    """The result of a bounded scroll or Load-More loop.

    Attributes:
        rounds: How many interaction rounds were performed.
        final_measure: The final progress measurement.
        stopped_reason: Why the loop stopped (progress-stalled, max-rounds,
            cancelled, or element-gone).
    """

    rounds: int
    final_measure: int
    stopped_reason: str


def scroll_until_stable(
    page: _Scrollable,
    measure: Callable[[_Scrollable], int],
    *,
    max_rounds: int = 20,
    no_progress_limit: int = 2,
    settle_seconds: float = 0.0,
    is_cancelled: Callable[[], bool] | None = None,
) -> ScrollOutcome:
    """Scroll a page until its content stops growing, within hard bounds.

    Args:
        page: The page to scroll.
        measure: Returns a monotonic progress figure (item count, content length).
        max_rounds: The absolute cap on scroll rounds.
        no_progress_limit: Stop after this many consecutive rounds without growth.
        settle_seconds: An optional wait after each scroll for content to load.
        is_cancelled: An optional cancellation check, polled each round.
    """
    previous = measure(page)
    stalls = 0
    rounds = 0
    while rounds < max_rounds:
        if is_cancelled is not None and is_cancelled():
            return ScrollOutcome(rounds=rounds, final_measure=previous, stopped_reason="cancelled")
        page.perform({"type": "scroll", "to": "bottom"})
        if settle_seconds > 0:
            page.wait(settle_seconds)
        rounds += 1
        current = measure(page)
        if current <= previous:
            stalls += 1
            if stalls >= no_progress_limit:
                return ScrollOutcome(
                    rounds=rounds, final_measure=current, stopped_reason="progress-stalled"
                )
        else:
            stalls = 0
        previous = current
    return ScrollOutcome(rounds=rounds, final_measure=previous, stopped_reason="max-rounds")


def click_until_gone(
    page: _Scrollable,
    selector: str,
    present: Callable[[_Scrollable], bool],
    *,
    max_clicks: int = 20,
    settle_seconds: float = 0.0,
    is_cancelled: Callable[[], bool] | None = None,
) -> ScrollOutcome:
    """Click a Load-More element until it disappears, within hard bounds.

    Args:
        page: The page to interact with.
        selector: The element to click each round.
        present: Returns whether the element is still present and actionable.
        max_clicks: The absolute cap on clicks.
        settle_seconds: An optional wait after each click.
        is_cancelled: An optional cancellation check, polled each round.
    """
    clicks = 0
    while clicks < max_clicks:
        if is_cancelled is not None and is_cancelled():
            return ScrollOutcome(rounds=clicks, final_measure=clicks, stopped_reason="cancelled")
        if not present(page):
            return ScrollOutcome(rounds=clicks, final_measure=clicks, stopped_reason="element-gone")
        page.perform({"type": "click", "selector": selector})
        if settle_seconds > 0:
            page.wait(settle_seconds)
        clicks += 1
    return ScrollOutcome(rounds=clicks, final_measure=clicks, stopped_reason="max-rounds")
