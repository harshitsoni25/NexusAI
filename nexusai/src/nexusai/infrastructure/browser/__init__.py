"""Browser automation: Playwright driver, context pooling, screenshot capture.

Introduced in the browser strategy phase.
"""

from __future__ import annotations

from nexusai.infrastructure.retrieval.browser import (
    BrowserDriver,
    BrowserPage,
    BrowserProvider,
)
from nexusai.infrastructure.retrieval.playwright_driver import (
    PlaywrightBrowserDriver,
)

__all__ = ["BrowserDriver", "BrowserPage", "BrowserProvider", "PlaywrightBrowserDriver"]
