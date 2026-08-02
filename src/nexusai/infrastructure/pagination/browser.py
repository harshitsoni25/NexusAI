"""Browser-interaction pagination: infinite scroll and load-more.

Where query pagination rewrites a URL, these strategies re-render the same URL
with one more interaction each step -- a scroll, or a click on a "load more"
button -- accumulating the interactions in the request's browser directives. The
provider that honours those directives is a browser provider; the strategy itself
still performs no retrieval, so it remains a pure derivation the engine drives.

Progress is counted in a private request label, so a strategy instance carries no
run state and can be shared across concurrent pagination loops.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from nexusai.domain.model.retrieval import (
    BrowserDirectives,
    Document,
    RetrievalRequest,
    replace_request,
)


def _append_action(
    request: RetrievalRequest, action: Mapping[str, object], label: str, limit: int
) -> RetrievalRequest | None:
    """Return ``request`` with one more action appended, or ``None`` at the limit."""
    count = int(request.labels.get(label, "0"))
    if count >= limit:
        return None
    base = request.browser or BrowserDirectives()
    actions: Sequence[Mapping[str, object]] = (*base.actions, dict(action))
    directives = BrowserDirectives(
        render=base.render,
        wait_for_selector=base.wait_for_selector,
        wait_for_timeout_seconds=base.wait_for_timeout_seconds,
        capture_screenshot=base.capture_screenshot,
        full_page_screenshot=base.full_page_screenshot,
        actions=actions,
    )
    advanced = replace_request(request, browser=directives)
    return replace_request(advanced, labels={**advanced.labels, label: str(count + 1)})


class InfiniteScrollStrategy:
    """Pages by scrolling the same page a bounded number of times.

    Args:
        max_scrolls: The maximum number of scroll interactions to accumulate.
        pixels: How far each scroll advances.
    """

    name = "infinite-scroll"

    def __init__(self, *, max_scrolls: int = 10, pixels: int = 2000) -> None:
        self._max_scrolls = max_scrolls
        self._pixels = pixels

    def next_request(
        self, request: RetrievalRequest, document: Document
    ) -> RetrievalRequest | None:
        """Return the request with one more scroll, or ``None`` at the limit."""
        if not document.is_success:
            return None
        return _append_action(
            request,
            {"type": "scroll", "pixels": self._pixels},
            "_scrolls",
            self._max_scrolls,
        )


class LoadMoreStrategy:
    """Pages by clicking a "load more" control a bounded number of times.

    Args:
        selector: The CSS selector of the control to click.
        max_clicks: The maximum number of clicks to accumulate.
    """

    name = "load-more"

    def __init__(self, selector: str, *, max_clicks: int = 10) -> None:
        self._selector = selector
        self._max_clicks = max_clicks

    def next_request(
        self, request: RetrievalRequest, document: Document
    ) -> RetrievalRequest | None:
        """Return the request with one more click, or ``None`` at the limit."""
        if not document.is_success:
            return None
        return _append_action(
            request,
            {"type": "click", "selector": self._selector},
            "_load_more",
            self._max_clicks,
        )
