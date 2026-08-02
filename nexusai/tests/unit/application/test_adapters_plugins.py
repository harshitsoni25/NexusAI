"""Tests for site-adapter resolution and plugin resolution."""

from __future__ import annotations

import pytest

from nexusai.application.adapters import (
    AdapterRegistry,
    AdapterResolutionError,
    ExampleCatalogAdapter,
    GenericHtmlAdapter,
)
from nexusai.application.plugins import PluginResolver
from nexusai.domain.errors.exceptions import PluginError
from nexusai.domain.model.plugin import ExtensionPoint
from nexusai.infrastructure.plugins.registry import InMemoryPluginRegistry


class TestAdapterResolution:
    def test_single_match_resolves(self) -> None:
        registry = AdapterRegistry([ExampleCatalogAdapter()])
        assert registry.resolve("https://catalog.example.com/x").name == "example-catalog"

    def test_no_match_raises(self) -> None:
        registry = AdapterRegistry([ExampleCatalogAdapter()])
        with pytest.raises(AdapterResolutionError):
            registry.resolve("https://other.com")

    def test_default_fallback(self) -> None:
        registry = AdapterRegistry([ExampleCatalogAdapter()])
        resolved = registry.resolve("https://other.com", default="example-catalog")
        assert resolved.name == "example-catalog"

    def test_ambiguous_match_raises(self) -> None:
        registry = AdapterRegistry([GenericHtmlAdapter(), ExampleCatalogAdapter()])
        with pytest.raises(AdapterResolutionError):
            registry.resolve("https://catalog.example.com/x")

    def test_explicit_wins(self) -> None:
        registry = AdapterRegistry([GenericHtmlAdapter(), ExampleCatalogAdapter()])
        resolved = registry.resolve("https://catalog.example.com/x", explicit="generic-html")
        assert resolved.name == "generic-html"

    def test_unknown_explicit_raises(self) -> None:
        with pytest.raises(AdapterResolutionError):
            AdapterRegistry([GenericHtmlAdapter()]).resolve("https://x", explicit="ghost")

    def test_adapter_provides_schema_and_urls(self) -> None:
        adapter = GenericHtmlAdapter()
        assert adapter.matches("https://x")
        assert adapter.start_urls("https://x") == ("https://x",)
        assert "title" in adapter.extraction_schema()


class TestPluginResolution:
    def test_unknown_plugin_is_rejected(self) -> None:
        resolver = PluginResolver(InMemoryPluginRegistry())
        with pytest.raises(PluginError):
            resolver.resolve(ExtensionPoint.EXPORTER, "ghost")
