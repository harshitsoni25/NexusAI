"""Real-browser certification tests (Phase 10R-CV, closing CB-1).

Each test is marked ``browser`` and drives Nexus AI's real Playwright driver and
browser provider against the controlled loopback site -- no fake page, no mocked
Playwright. When the browser binary is unavailable the tests skip (BLOCKED), so they
are collectable everywhere but only execute where a real browser exists.

The suite proves the runtime chain the fake-page unit tests cannot: Playwright ->
adapter -> Nexus AI model, for JavaScript rendering, lazy loading, bounded infinite
scroll, Load More, four-stage screenshots, network observation, provenance, visual
comparison, DOM change, cleanup and timeout.
"""

from __future__ import annotations

from collections.abc import Iterator
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest

from nexusai.domain.errors.exceptions import BrowserError
from nexusai.domain.model.retrieval import (
    BrowserDirectives,
    RetrievalMethod,
    RetrievalRequest,
)
from nexusai.infrastructure.retrieval.artifacts import FilesystemArtifactWriter
from nexusai.infrastructure.retrieval.browser import BrowserProvider
from nexusai.infrastructure.retrieval.playwright_driver import PlaywrightBrowserDriver
from nexusai.infrastructure.visual import ScreenshotComparator
from nexusai.testing import FrozenClock

pytestmark = pytest.mark.browser


import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cert_server import serve


@pytest.fixture(scope="session")
def cert_base_url() -> Iterator[str]:
    """Run the controlled certification site for the session; yield its base URL."""
    with serve() as base_url:
        yield base_url


@pytest.fixture
def chromium() -> Iterator[Any]:
    """Yield a launched real Chromium browser, or skip if unavailable."""
    sync_api = pytest.importorskip(
        "playwright.sync_api", reason="Playwright not installed (browser extra absent)"
    )
    try:
        playwright = sync_api.sync_playwright().start()
    except Exception as exc:  # noqa: BLE001 - report as a skip, not an error
        pytest.skip(f"Playwright could not start: {exc}")
    try:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:  # noqa: BLE001 - missing binary -> BLOCKED
            pytest.skip(f"Chromium binary unavailable: {exc}")
        try:
            yield browser
        finally:
            browser.close()
    finally:
        playwright.stop()


@pytest.fixture
def provider(tmp_path: Path) -> Iterator[BrowserProvider]:
    """A started Nexus AI browser provider, or skip if the binary is unavailable."""
    pytest.importorskip("playwright.sync_api", reason="Playwright not installed")
    driver = PlaywrightBrowserDriver(headless=True)
    artifacts = FilesystemArtifactWriter(tmp_path)
    prov = BrowserProvider(driver, FrozenClock(), artifact_writer=artifacts)
    try:
        prov.initialize()
    except Exception as exc:  # noqa: BLE001 - missing binary -> BLOCKED
        pytest.skip(f"Chromium binary unavailable: {exc}")
    try:
        yield prov
    finally:
        prov.dispose()


def _request(url: str, directives: BrowserDirectives) -> RetrievalRequest:
    return RetrievalRequest(url=url, method=RetrievalMethod.BROWSER, browser=directives)


class TestSmoke:
    def test_real_browser_launches_and_renders_local_page(
        self, chromium: Any, cert_base_url: str
    ) -> None:
        context = chromium.new_context()
        page = context.new_page()
        page.goto(f"{cert_base_url}/static")
        assert page.query_selector("#items") is not None
        assert len(page.query_selector_all(".item")) == 3
        context.close()


class TestJavaScriptRendering:
    def test_js_injected_content_is_extracted(
        self, provider: BrowserProvider, cert_base_url: str
    ) -> None:
        document = provider.retrieve(
            _request(f"{cert_base_url}/javascript", BrowserDirectives(wait_for_selector="#items"))
        )
        html = document.content.decode("utf-8")
        assert "One" in html and "Two" in html and "Three" in html


class TestLazyLoading:
    def test_lazy_content_loads_and_terminates(
        self, provider: BrowserProvider, cert_base_url: str
    ) -> None:
        document = provider.retrieve(
            _request(
                f"{cert_base_url}/lazy", BrowserDirectives(lazy_load=True, lazy_load_max_rounds=10)
            )
        )
        assert document.content.decode("utf-8").count('class="item"') == 5


class TestInfiniteScroll:
    def test_infinite_scroll_grows_then_stabilises(
        self, provider: BrowserProvider, cert_base_url: str
    ) -> None:
        document = provider.retrieve(
            _request(
                f"{cert_base_url}/infinite-scroll",
                BrowserDirectives(lazy_load=True, lazy_load_max_rounds=15),
            )
        )
        assert document.content.decode("utf-8").count('class="item"') == 9


class TestLoadMore:
    def test_load_more_clicks_reveal_all_records(
        self, provider: BrowserProvider, cert_base_url: str
    ) -> None:
        actions = [{"type": "click", "selector": "#more"} for _ in range(3)]
        document = provider.retrieve(
            _request(f"{cert_base_url}/load-more", BrowserDirectives(actions=actions))
        )
        assert document.content.decode("utf-8").count('class="item"') == 6


class TestFourStageScreenshots:
    def test_four_lifecycle_screenshots_are_written(
        self, provider: BrowserProvider, cert_base_url: str
    ) -> None:
        document = provider.retrieve(
            _request(
                f"{cert_base_url}/infinite-scroll",
                BrowserDirectives(lazy_load=True, staged_screenshots=True),
            )
        )
        assert len(document.screenshots) == 4
        stages = [ref.locator for ref in document.screenshots]
        assert any("initial" in s for s in stages)
        assert any("loaded" in s for s in stages)
        assert any("scrolled" in s for s in stages)
        assert any("post-extraction" in s for s in stages)
        assert all(_is_png(_read(ref.locator)) for ref in document.screenshots)


class TestNetworkObservation:
    def test_page_network_activity_is_observed(
        self, provider: BrowserProvider, cert_base_url: str
    ) -> None:
        document = provider.retrieve(
            _request(
                f"{cert_base_url}/api-page",
                BrowserDirectives(wait_for_selector="#items", observe_network=True),
            )
        )
        assert document.network is not None
        urls = [r.url for r in document.network.requests]
        assert any("/api-json" in u for u in urls)
        assert document.network.total_requests >= 1


class TestProvenance:
    def test_browser_provenance_is_recorded(
        self, provider: BrowserProvider, cert_base_url: str
    ) -> None:
        document = provider.retrieve(_request(f"{cert_base_url}/static", BrowserDirectives()))
        assert document.source is not None
        assert document.source.method == "browser"
        assert document.source.attributes["rendered"] is True
        assert cert_base_url in str(document.source.attributes["final_url"])


class TestVisualValidation:
    def test_baseline_vs_baseline_passes_and_changed_differs(
        self, provider: BrowserProvider, cert_base_url: str
    ) -> None:
        shot = BrowserDirectives(capture_screenshot=True)
        base = provider.retrieve(_request(f"{cert_base_url}/visual/baseline", shot))
        changed = provider.retrieve(_request(f"{cert_base_url}/visual/changed", shot))
        # Re-capture the same baseline for an identical comparison.
        base2 = provider.retrieve(_request(f"{cert_base_url}/visual/baseline", shot))
        assert base.screenshot is not None
        assert changed.screenshot is not None
        assert base2.screenshot is not None
        comparator = ScreenshotComparator()
        base_bytes = _read(base.screenshot.locator)
        same, _ = comparator.compare(base_bytes, _read(base2.screenshot.locator))
        diff, _ = comparator.compare(base_bytes, _read(changed.screenshot.locator))
        assert same.difference_ratio == 0.0
        assert diff.difference_ratio > same.difference_ratio


class TestDomChange:
    def test_rendered_dom_reflects_controlled_change(
        self, provider: BrowserProvider, cert_base_url: str
    ) -> None:
        base = provider.retrieve(_request(f"{cert_base_url}/dom/baseline", BrowserDirectives()))
        changed = provider.retrieve(_request(f"{cert_base_url}/dom/changed", BrowserDirectives()))
        assert base.content != changed.content
        assert b"B-modified" in changed.content


class TestCleanup:
    def test_provider_disposes_without_leaking(self, tmp_path: Path, cert_base_url: str) -> None:
        pytest.importorskip("playwright.sync_api", reason="Playwright not installed")
        driver = PlaywrightBrowserDriver(headless=True)
        prov = BrowserProvider(
            driver, FrozenClock(), artifact_writer=FilesystemArtifactWriter(tmp_path)
        )
        try:
            prov.initialize()
        except Exception as exc:  # noqa: BLE001
            pytest.skip(f"Chromium binary unavailable: {exc}")
        prov.retrieve(_request(f"{cert_base_url}/static", BrowserDirectives()))
        prov.dispose()  # must not raise; browser is stopped
        prov.dispose()  # idempotent second dispose


class TestTimeout:
    def test_slow_page_times_out_with_browser_error(
        self, provider: BrowserProvider, cert_base_url: str
    ) -> None:
        with pytest.raises(BrowserError):
            provider.retrieve(
                _request(
                    f"{cert_base_url}/slow",
                    BrowserDirectives(wait_for_selector="#never-appears"),
                ),
            )


def _read(locator: str) -> bytes:
    return Path(locator).read_bytes()


def _is_png(data: bytes) -> bool:
    from PIL import Image

    Image.open(BytesIO(data)).verify()
    return True
