"""Retrieval providers: one transport each, one unified document out.

Each provider owns a single transport -- HTTP, browser, API -- implements the
:class:`~nexusai.domain.ports.retrieval.RetrievalProvider` contract, and
returns the unified :class:`~nexusai.domain.model.retrieval.Document`. A
provider translates its library's exceptions into the framework hierarchy at its
own boundary, so no ``httpx`` or Playwright exception escapes into the engine.
"""

from __future__ import annotations

from nexusai.infrastructure.retrieval.api import ApiProvider
from nexusai.infrastructure.retrieval.browser import BrowserProvider
from nexusai.infrastructure.retrieval.http import HttpProvider

__all__ = ["ApiProvider", "BrowserProvider", "HttpProvider"]
