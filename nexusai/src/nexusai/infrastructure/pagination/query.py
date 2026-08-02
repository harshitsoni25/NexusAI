"""Query-parameter pagination: page number, offset, cursor.

These three page by rewriting the request's query string, so they work over any
transport -- there is nothing browser-specific about incrementing ``?page=``.
Progress lives in the request itself (its params, or a private label counter),
which keeps the strategies free of hidden state and safe to reuse across runs.
"""

from __future__ import annotations

from collections.abc import Callable

from nexusai.domain.model.retrieval import Document, RetrievalRequest, replace_request

HasNext = Callable[[Document], bool]
"""A predicate deciding whether more pages follow the given document."""

NextCursor = Callable[[Document], str | None]
"""Extracts the next-page cursor from a document, or ``None`` when there is none."""


def _stop_on_error(document: Document, has_next: HasNext | None) -> bool:
    """Stop paging on a non-success status or when the predicate says so."""
    if not document.is_success:
        return True
    return has_next is not None and not has_next(document)


class PageNumberStrategy:
    """Pages by incrementing a page-number query parameter.

    Args:
        param: The query parameter carrying the page number.
        start: The number of the first page.
        max_pages: A hard ceiling so a broken ``has_next`` cannot loop forever.
        has_next: An optional predicate to stop early, e.g. on an empty page.
    """

    name = "page-number"

    def __init__(
        self,
        *,
        param: str = "page",
        start: int = 1,
        max_pages: int = 50,
        has_next: HasNext | None = None,
    ) -> None:
        self._param = param
        self._start = start
        self._max_pages = max_pages
        self._has_next = has_next

    def next_request(
        self, request: RetrievalRequest, document: Document
    ) -> RetrievalRequest | None:
        """Return the request for the next page, or ``None`` when exhausted."""
        if _stop_on_error(document, self._has_next):
            return None
        current = int(request.params.get(self._param, str(self._start)))
        next_page = current + 1
        if next_page - self._start >= self._max_pages:
            return None
        return request.with_params(**{self._param: str(next_page)})


class OffsetStrategy:
    """Pages by advancing an offset parameter by a fixed limit.

    Args:
        offset_param: The query parameter carrying the offset.
        limit_param: The query parameter carrying the page size.
        limit: The page size, added to the offset each step.
        max_items: A hard ceiling on the offset.
        has_next: An optional predicate to stop early.
    """

    name = "offset"

    def __init__(
        self,
        *,
        offset_param: str = "offset",
        limit_param: str = "limit",
        limit: int = 20,
        max_items: int = 1000,
        has_next: HasNext | None = None,
    ) -> None:
        self._offset_param = offset_param
        self._limit_param = limit_param
        self._limit = limit
        self._max_items = max_items
        self._has_next = has_next

    def next_request(
        self, request: RetrievalRequest, document: Document
    ) -> RetrievalRequest | None:
        """Return the request for the next offset window, or ``None``."""
        if _stop_on_error(document, self._has_next):
            return None
        current = int(request.params.get(self._offset_param, "0"))
        next_offset = current + self._limit
        if next_offset >= self._max_items:
            return None
        return request.with_params(
            **{self._offset_param: str(next_offset), self._limit_param: str(self._limit)}
        )


class CursorStrategy:
    """Pages by following an opaque cursor read from each document.

    The cursor is extracted by a supplied callable -- typically reading a JSON
    field -- so the strategy stays independent of the response shape. Paging stops
    when the extractor returns ``None`` or the same cursor twice, which guards
    against an endpoint that echoes its cursor forever.

    Args:
        cursor_param: The query parameter carrying the cursor.
        next_cursor: A callable returning the next cursor from a document.
        max_pages: A hard ceiling on the number of pages.
    """

    name = "cursor"

    def __init__(
        self,
        next_cursor: NextCursor,
        *,
        cursor_param: str = "cursor",
        max_pages: int = 100,
    ) -> None:
        self._next_cursor = next_cursor
        self._cursor_param = cursor_param
        self._max_pages = max_pages

    def next_request(
        self, request: RetrievalRequest, document: Document
    ) -> RetrievalRequest | None:
        """Return the request for the next cursor, or ``None`` when exhausted."""
        if not document.is_success:
            return None
        seen = int(request.labels.get("_cursor_page", "0"))
        if seen >= self._max_pages:
            return None
        cursor = self._next_cursor(document)
        if not cursor or cursor == request.params.get(self._cursor_param):
            return None
        advanced = request.with_params(**{self._cursor_param: cursor})
        return replace_request(advanced, labels={**advanced.labels, "_cursor_page": str(seen + 1)})
