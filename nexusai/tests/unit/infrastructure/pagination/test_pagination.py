"""Tests for the pagination strategies."""

from __future__ import annotations

from datetime import UTC, datetime

from nexusai.domain.model.retrieval import (
    Document,
    RetrievalMethod,
    RetrievalRequest,
)
from nexusai.infrastructure.pagination import (
    CursorStrategy,
    InfiniteScrollStrategy,
    LoadMoreStrategy,
    OffsetStrategy,
    PageNumberStrategy,
)


def _doc(status: int = 200) -> Document:
    return Document(
        url="https://x/list",
        content=b"{}",
        status_code=status,
        provider="http",
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        media_type="application/json",
    )


def _request(**overrides: object) -> RetrievalRequest:
    return RetrievalRequest(url="https://x/list", **overrides)  # type: ignore[arg-type]


def test_page_number_advances_and_respects_ceiling() -> None:
    strategy = PageNumberStrategy(max_pages=3)
    first = strategy.next_request(_request(), _doc())
    assert first is not None
    assert first.params["page"] == "2"
    at_limit = strategy.next_request(_request(params={"page": "3"}), _doc())
    assert at_limit is None


def test_page_number_stops_on_error_status() -> None:
    assert PageNumberStrategy().next_request(_request(), _doc(404)) is None


def test_page_number_honours_has_next_predicate() -> None:
    strategy = PageNumberStrategy(has_next=lambda _document: False)
    assert strategy.next_request(_request(), _doc()) is None


def test_offset_advances_by_limit_and_stops_at_max() -> None:
    strategy = OffsetStrategy(limit=20, max_items=40)
    first = strategy.next_request(_request(), _doc())
    assert first is not None
    assert first.params == {"offset": "20", "limit": "20"}
    assert strategy.next_request(_request(params={"offset": "20"}), _doc()) is None


def test_cursor_follows_extracted_cursor_then_stops() -> None:
    cursors = iter(["c1", None])
    strategy = CursorStrategy(lambda _document: next(cursors))
    first = strategy.next_request(_request(), _doc())
    assert first is not None
    assert first.params["cursor"] == "c1"
    assert first.labels["_cursor_page"] == "1"
    assert strategy.next_request(first, _doc()) is None


def test_cursor_stops_on_repeated_cursor() -> None:
    strategy = CursorStrategy(lambda _document: "same")
    request = _request(params={"cursor": "same"})
    assert strategy.next_request(request, _doc()) is None


def test_cursor_respects_max_pages() -> None:
    strategy = CursorStrategy(lambda _document: "c", max_pages=1)
    request = _request(labels={"_cursor_page": "1"})
    assert strategy.next_request(request, _doc()) is None


def test_infinite_scroll_accumulates_scroll_actions() -> None:
    strategy = InfiniteScrollStrategy(max_scrolls=2)
    request = _request(method=RetrievalMethod.BROWSER)
    first = strategy.next_request(request, _doc())
    assert first is not None
    assert [action["type"] for action in first.browser.actions] == ["scroll"]  # type: ignore[union-attr]
    assert first.labels["_scrolls"] == "1"
    second = strategy.next_request(first, _doc())
    assert second is not None
    assert strategy.next_request(second, _doc()) is None


def test_load_more_accumulates_click_actions() -> None:
    strategy = LoadMoreStrategy("#more", max_clicks=1)
    request = _request(method=RetrievalMethod.BROWSER)
    first = strategy.next_request(request, _doc())
    assert first is not None
    action = first.browser.actions[0]  # type: ignore[union-attr]
    assert action == {"type": "click", "selector": "#more"}
    assert strategy.next_request(first, _doc()) is None


def test_browser_strategies_stop_on_error_status() -> None:
    assert InfiniteScrollStrategy().next_request(_request(), _doc(500)) is None
    assert LoadMoreStrategy("#m").next_request(_request(), _doc(500)) is None
