"""Small example site adapters.

These show the shape an adapter takes: a name and version, a target-matching
rule, starting URLs, an extraction schema and a preferences map. They are
configuration, not engine code -- a real deployment would add its own adapters the
same way, and adding one never touches the orchestrator or the engines.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from nexusai.shared.types import JsonValue


class GenericHtmlAdapter:
    """A permissive adapter matching any HTTP(S) target, for simple HTML sites."""

    name = "generic-html"
    version = "1.0"

    def matches(self, target: str) -> bool:
        """Match any http or https target."""
        return target.startswith(("http://", "https://"))

    def start_urls(self, target: str) -> Sequence[str]:
        """Begin retrieval at the target itself."""
        return (target,)

    def extraction_schema(self) -> Mapping[str, JsonValue]:
        """Extract a title and a body text by CSS selector."""
        return {"title": "title", "heading": "h1"}

    def preferences(self) -> Mapping[str, JsonValue]:
        """Prefer the HTTP strategy for a plain HTML site."""
        return {"strategy": "http"}


class ExampleCatalogAdapter:
    """An adapter for a fictional catalogue host, matching one domain."""

    name = "example-catalog"
    version = "1.0"

    def matches(self, target: str) -> bool:
        """Match the example catalogue domain only."""
        return "catalog.example.com" in target

    def start_urls(self, target: str) -> Sequence[str]:
        """Begin at the catalogue's product listing."""
        return (target.rstrip("/") + "/products",)

    def extraction_schema(self) -> Mapping[str, JsonValue]:
        """Extract product fields by CSS selector."""
        return {"name": ".product .name", "price": ".product .price"}

    def preferences(self) -> Mapping[str, JsonValue]:
        """Prefer HTTP; the catalogue serves static HTML."""
        return {"strategy": "http"}
