"""The retrieval engine and its supporting types.

The engine coordinates retrieval without owning a transport: it selects a
provider for a request, applies a recovery policy when one fails, and follows a
pagination strategy across pages. It performs no parsing and no extraction, and
returns only unified documents.
"""

from __future__ import annotations

from nexusai.application.retrieval.engine import RetrievalEngine, RetrievalOutcome

__all__ = ["RetrievalEngine", "RetrievalOutcome"]
