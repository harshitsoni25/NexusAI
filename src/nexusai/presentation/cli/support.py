"""Re-exports of application-service wiring for CLI commands.

The wiring itself lives in the composition root, which is the layer permitted to
touch infrastructure. Commands import from here for convenience; this module adds
no logic of its own.
"""

from __future__ import annotations

from nexusai.composition.application import (
    ApplicationServices,
    build_scrape_collaborators,
    build_services,
    database_path,
)

__all__ = [
    "ApplicationServices",
    "build_scrape_collaborators",
    "build_services",
    "database_path",
]
