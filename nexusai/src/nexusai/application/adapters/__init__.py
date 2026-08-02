"""Site adapters and their deterministic resolution."""

from __future__ import annotations

from nexusai.application.adapters.examples import (
    ExampleCatalogAdapter,
    GenericHtmlAdapter,
)
from nexusai.application.adapters.resolution import (
    AdapterRegistry,
    AdapterResolutionError,
)

__all__ = [
    "AdapterRegistry",
    "AdapterResolutionError",
    "ExampleCatalogAdapter",
    "GenericHtmlAdapter",
]
