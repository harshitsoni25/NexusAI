"""Backend service settings for the Nexus AI Pro API.

These configure the API process itself (host, port, docs, logging). They are kept
separate from the Nexus AI engine's own configuration, which is loaded by the
engine's ``bootstrap`` entry point. Engine behaviour is never overridden here; the
API only points the engine at a configuration file if one is supplied.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    """Runtime settings for the API service, populated from ``NEXUSAI_PRO_*`` env."""

    model_config = SettingsConfigDict(env_prefix="NEXUSAI_PRO_", extra="ignore")

    title: str = "Nexus AI Pro API"
    version: str = "0.1.0"
    description: str = (
        "REST interface over the certified Nexus AI engine. The engine is reused "
        "as an immutable library; this service adds no scraping logic of its own."
    )

    host: str = "127.0.0.1"
    port: int = 8000
    root_path: str = ""

    # Where interactive docs are served (set any to None to disable).
    docs_url: str | None = "/docs"
    redoc_url: str | None = "/redoc"
    openapi_url: str | None = "/openapi.json"

    # Passed through to the engine's ``bootstrap`` when building the container.
    engine_config_file: Path | None = None

    # Logging.
    log_level: str = "INFO"
    log_json: bool = True

    # Background scrape execution.
    max_concurrent_scrapes: int = Field(default=4, ge=1, le=64)

    # CORS origins for a future desktop/web client (empty = same-origin only).
    cors_origins: list[str] = Field(default_factory=list)

    api_prefix: str = "/api/v1"


@lru_cache
def get_settings() -> ApiSettings:
    """Return cached settings so the process reads the environment once."""
    return ApiSettings()
