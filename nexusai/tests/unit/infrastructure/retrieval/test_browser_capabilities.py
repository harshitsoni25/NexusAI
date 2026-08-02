"""Browser capability logic verified with a deterministic fake page.

These cover the Phase 10R-C gap closures — lazy loading, the four-stage screenshot
lifecycle, browser provenance, and network observation — as pure control-flow and
aggregation logic, using a scripted fake page. Real browser execution against a
live binary is verified separately and is environment-dependent; here the logic is
proven without a browser.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest

from nexusai.domain.model.network import ResourceType
from nexusai.domain.model.retrieval import (
    BrowserDirectives,
    RetrievalMethod,
    RetrievalRequest,
)
from nexusai.domain.provenance.source import ArtifactReference
from nexusai.infrastructure.retrieval.browser import BrowserProvider
from nexusai.testing import FrozenClock

pytestmark = pytest.mark.component


class GrowingPage:
    """A page that reveals more content on each scroll, then stabilises."""

    def __init__(
        self,
        *,
        growth: int = 20,
        cap: int = 60,
        requests: list[Mapping[str, object]] | None = None,
    ) -> None:
        self.items = 20
        self._growth = growth
        self._cap = cap
        self.shots = 0
        self._requests = requests or []

    def goto(self, url: str, timeout_seconds: float | None) -> int:
        return 200

    def wait_for_selector(self, selector: str, timeout_seconds: float | None) -> None:
        pass

    def wait(self, seconds: float) -> None:
        pass

    def perform(self, action: Mapping[str, object]) -> None:
        if action.get("type") == "scroll":
            self.items = min(self._cap, self.items + self._growth)

    def content(self) -> str:
        return "<html><body>" + "x" * self.items + "</body></html>"

    def current_url(self) -> str:
        return "https://mock.local/final"

    def screenshot(self, *, full_page: bool) -> bytes:
        self.shots += 1
        return f"PNG{self.shots}".encode()

    def captured_requests(self) -> Sequence[Mapping[str, object]]:
        return tuple(self._requests)

    def close(self) -> None:
        pass


class FakeDriver:
    def __init__(self, page: GrowingPage) -> None:
        self._page = page

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def new_page(self) -> GrowingPage:
        return self._page


class CountingArtifacts:
    def __init__(self) -> None:
        self.written: list[str] = []

    def write(self, name: str, data: bytes, media_type: str) -> ArtifactReference:
        self.written.append(name)
        return ArtifactReference(locator=name, media_type=media_type, size_bytes=len(data))


def _provider(page: GrowingPage, artifacts: CountingArtifacts | None = None) -> BrowserProvider:
    return BrowserProvider(FakeDriver(page), FrozenClock(), artifact_writer=artifacts)


def _request(directives: BrowserDirectives) -> RetrievalRequest:
    return RetrievalRequest(
        url="https://mock.local/", method=RetrievalMethod.BROWSER, browser=directives
    )


class TestLazyLoading:
    def test_lazy_load_scrolls_until_content_stabilises(self) -> None:
        page = GrowingPage(growth=20, cap=60)
        provider = _provider(page)
        provider.retrieve(_request(BrowserDirectives(lazy_load=True, lazy_load_max_rounds=10)))
        assert page.items == 60  # grew from 20 to the cap via bounded scrolling

    def test_lazy_load_is_bounded(self) -> None:
        page = GrowingPage(growth=1, cap=10_000)  # never stabilises
        provider = _provider(page)
        # Must terminate despite unbounded growth.
        provider.retrieve(_request(BrowserDirectives(lazy_load=True, lazy_load_max_rounds=5)))


class TestStagedScreenshots:
    def test_four_stage_lifecycle_captured(self) -> None:
        page = GrowingPage()
        artifacts = CountingArtifacts()
        provider = _provider(page, artifacts)
        provider.retrieve(_request(BrowserDirectives(lazy_load=True, staged_screenshots=True)))
        stages = [
            next(
                (s for s in ("initial", "loaded", "scrolled", "post-extraction") if f"-{s}-" in n),
                "?",
            )
            for n in artifacts.written
            if n.startswith("screenshot-")
        ]
        assert stages == ["initial", "loaded", "scrolled", "post-extraction"]

    def test_no_staged_screenshots_without_flag(self) -> None:
        page = GrowingPage()
        artifacts = CountingArtifacts()
        _provider(page, artifacts).retrieve(_request(BrowserDirectives()))
        assert artifacts.written == []


class TestBrowserProvenance:
    def test_source_records_browser_method_and_attributes(self) -> None:
        page = GrowingPage()
        document = _provider(page).retrieve(_request(BrowserDirectives(render=True)))
        assert document.source is not None
        assert document.source.method == "browser"
        assert document.source.attributes["rendered"] is True
        assert document.source.attributes["final_url"] == "https://mock.local/final"

    def test_provenance_carries_content_hash(self) -> None:
        page = GrowingPage()
        document = _provider(page).retrieve(_request(BrowserDirectives()))
        assert document.source is not None
        assert document.source.content_hash


class TestNetworkObservation:
    def test_observed_requests_are_summarised(self) -> None:
        requests: list[Mapping[str, object]] = [
            {
                "url": "https://mock.local/api",
                "method": "GET",
                "status": 200,
                "type": "xhr",
                "size_bytes": 400,
            },
            {"url": "https://mock.local/gql", "method": "POST", "status": 200, "type": "fetch"},
            {
                "url": "https://mock.local/logo.png",
                "method": "GET",
                "status": 200,
                "type": "image",
                "size_bytes": 900,
            },
            {"url": "https://mock.local/dead", "method": "GET", "status": 500, "type": "xhr"},
        ]
        page = GrowingPage(requests=requests)
        document = _provider(page).retrieve(_request(BrowserDirectives(observe_network=True)))
        assert document.network is not None
        assert document.network.total_requests == 4
        assert document.network.failed_requests == 1
        assert len(document.network.api_requests) == 3  # 2 xhr + 1 fetch
        assert document.network.total_bytes == 1300
        assert document.network.by_resource_type[ResourceType.IMAGE.value] == 1

    def test_no_network_observation_without_flag(self) -> None:
        page = GrowingPage(requests=[{"url": "x", "method": "GET", "status": 200, "type": "xhr"}])
        document = _provider(page).retrieve(_request(BrowserDirectives()))
        assert document.network is None
