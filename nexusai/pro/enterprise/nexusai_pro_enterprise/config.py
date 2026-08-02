"""Enterprise configuration (12-factor: everything from the environment).

Cloud-ready: no config is hard-coded. The signing secret, token lifetime, password
policy and persistence backend are all injected from the environment so the same image
runs anywhere and scales horizontally.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class EnterpriseConfig:
    secret_key: str = os.environ.get("NEXUSAI_ENT_SECRET", "dev-insecure-change-me")
    token_ttl_seconds: int = int(os.environ.get("NEXUSAI_ENT_TOKEN_TTL", "3600"))
    issuer: str = os.environ.get("NEXUSAI_ENT_ISSUER", "nexusai-pro")
    min_password_length: int = int(os.environ.get("NEXUSAI_ENT_MIN_PW", "10"))
    backend: str = os.environ.get("NEXUSAI_ENT_BACKEND", "memory")
    database_url: str | None = os.environ.get("NEXUSAI_ENT_DATABASE_URL")
    api_key_prefix: str = os.environ.get("NEXUSAI_ENT_KEY_PREFIX", "hk")

    def require_production_secret(self) -> None:
        if self.secret_key == "dev-insecure-change-me":
            raise RuntimeError("NEXUSAI_ENT_SECRET must be set outside development")
