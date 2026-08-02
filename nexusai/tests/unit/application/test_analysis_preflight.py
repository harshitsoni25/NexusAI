"""Tests for the analyzer, strategy recommendation, and robots preflight."""

from __future__ import annotations

from application_builders import make_document
from nexusai.application.analysis import SiteAnalyzer, StrategyRecommender
from nexusai.domain.model.analysis import (
    AnalysisResult,
    Characteristic,
    Confidence,
    Observation,
    RetrievalStrategy,
)
from nexusai.domain.policy.strategy_recommendation import (
    apply_override,
    recommend_strategy,
)
from nexusai.infrastructure.analysis import analyse_html
from nexusai.infrastructure.preflight import absent_robots, parse_robots

_RICH_HTML = (
    b"<html><head><script type='application/ld+json'>{}</script>"
    b"<meta property='og:title' content='x'></head><body>"
    + b"product listing text " * 30
    + b"<table><tr><td>1</td></tr></table>"
    b"<a href='/data.csv'>download</a><link rel='next' href='/p2'></body></html>"
)


class TestDetection:
    def test_detects_expected_characteristics(self) -> None:
        result = analyse_html("https://shop/products", _RICH_HTML)
        assert result.has(Characteristic.STATIC_HTML)
        assert result.has(Characteristic.PAGINATION)
        assert result.has(Characteristic.TABLES)
        assert result.has(Characteristic.JSON_LD)
        assert result.has(Characteristic.DOWNLOADABLE)

    def test_pagination_from_next_link_is_high_confidence(self) -> None:
        result = analyse_html("https://x", _RICH_HTML)
        assert result.confidence_of(Characteristic.PAGINATION) is Confidence.HIGH

    def test_empty_page_warns(self) -> None:
        result = analyse_html("https://x", b"<html></html>")
        assert result.warnings


class TestRecommendation:
    def test_static_recommends_http(self) -> None:
        analysis = AnalysisResult(
            target="x",
            observations=[
                Observation(characteristic=Characteristic.STATIC_HTML, confidence=Confidence.HIGH)
            ],
        )
        assert recommend_strategy(analysis).strategy is RetrievalStrategy.HTTP

    def test_infinite_scroll_recommends_browser(self) -> None:
        analysis = AnalysisResult(
            target="x",
            observations=[
                Observation(
                    characteristic=Characteristic.INFINITE_SCROLL, confidence=Confidence.MEDIUM
                )
            ],
        )
        assert recommend_strategy(analysis).strategy is RetrievalStrategy.BROWSER

    def test_api_endpoint_recommends_api(self) -> None:
        analysis = AnalysisResult(
            target="x",
            observations=[
                Observation(characteristic=Characteristic.REST_ENDPOINT, confidence=Confidence.HIGH)
            ],
        )
        assert recommend_strategy(analysis).strategy is RetrievalStrategy.API

    def test_static_plus_dynamic_recommends_hybrid(self) -> None:
        analysis = AnalysisResult(
            target="x",
            observations=[
                Observation(characteristic=Characteristic.STATIC_HTML, confidence=Confidence.HIGH),
                Observation(characteristic=Characteristic.LOAD_MORE, confidence=Confidence.LOW),
            ],
        )
        assert recommend_strategy(analysis).strategy is RetrievalStrategy.HYBRID

    def test_override_is_recorded(self) -> None:
        analysis = AnalysisResult(
            target="x",
            observations=[
                Observation(characteristic=Characteristic.STATIC_HTML, confidence=Confidence.HIGH)
            ],
        )
        overridden = apply_override(recommend_strategy(analysis), RetrievalStrategy.BROWSER)
        assert overridden.strategy is RetrievalStrategy.BROWSER
        assert overridden.overridden


class TestAnalyzerService:
    def test_analyse_separates_from_recommend(self) -> None:
        analyzer = SiteAnalyzer(lambda t: make_document(body=_RICH_HTML), analyse_html)
        analysis = analyzer.analyse("https://x")
        recommendation = StrategyRecommender().recommend(analysis)
        assert isinstance(analysis, AnalysisResult)
        assert recommendation.strategy is RetrievalStrategy.HTTP

    def test_recommender_applies_override(self) -> None:
        analysis = analyse_html("https://x", _RICH_HTML)
        recommendation = StrategyRecommender().recommend(
            analysis, override=RetrievalStrategy.BROWSER
        )
        assert recommendation.overridden


class TestRobotsPreflight:
    _ROBOTS = (
        "User-agent: *\nDisallow: /private\nAllow: /private/public\n"
        "Crawl-delay: 2\nSitemap: https://shop/sitemap.xml"
    )

    def test_allowed_path(self) -> None:
        result = parse_robots(self._ROBOTS, target="https://shop/products")
        assert result.allowed
        assert result.crawl_delay == 2.0
        assert result.sitemaps == ("https://shop/sitemap.xml",)

    def test_disallowed_path(self) -> None:
        assert not parse_robots(self._ROBOTS, target="https://shop/private/x").allowed

    def test_allow_overrides_disallow_by_specificity(self) -> None:
        assert parse_robots(self._ROBOTS, target="https://shop/private/public/ok").allowed

    def test_absent_robots_is_permissive_but_flagged(self) -> None:
        result = absent_robots("https://x")
        assert result.allowed
        assert not result.robots_present
        assert result.warnings
