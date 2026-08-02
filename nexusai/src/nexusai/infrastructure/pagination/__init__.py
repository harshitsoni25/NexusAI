"""Interchangeable pagination strategies.

Each strategy derives the next :class:`RetrievalRequest` from the current request
and the document it produced, returning ``None`` when the sequence is exhausted.
No strategy fetches anything -- the engine drives the loop -- so all of them are
testable with a document in hand and no network, and a new one is added by
registering it rather than by touching the engine.
"""

from __future__ import annotations

from nexusai.infrastructure.pagination.browser import (
    InfiniteScrollStrategy,
    LoadMoreStrategy,
)
from nexusai.infrastructure.pagination.query import (
    CursorStrategy,
    OffsetStrategy,
    PageNumberStrategy,
)

__all__ = [
    "CursorStrategy",
    "InfiniteScrollStrategy",
    "LoadMoreStrategy",
    "OffsetStrategy",
    "PageNumberStrategy",
]
