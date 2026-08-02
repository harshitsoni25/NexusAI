"""The composition root for the enterprise layer.

Wires repositories (chosen by config: in-memory today, a cloud store tomorrow) and the
services on top of them. Everything downstream depends on this container, so swapping
the persistence backend or the token secret is a single wiring decision made here.
"""

from __future__ import annotations

from ..adapters.memory import (
    InMemoryApiKeyRepository,
    InMemoryAuditRepository,
    InMemoryProjectRepository,
    InMemoryRoleRepository,
    InMemoryTeamRepository,
    InMemoryUserRepository,
    InMemoryWorkspaceRepository,
)
from ..config import EnterpriseConfig
from ..security.tokens import TokenService
from ..services.apikey_service import ApiKeyService
from ..services.audit_service import AuditService
from ..services.auth_service import AuthService
from ..services.project_service import ProjectService
from ..services.rbac import Authorizer
from ..services.team_service import TeamService
from ..services.user_service import UserService
from ..services.workspace_service import WorkspaceService


class EnterpriseContainer:
    """Holds every wired service. Build once per process."""

    def __init__(self, config: EnterpriseConfig | None = None) -> None:
        self.config = config or EnterpriseConfig()

        # Repositories — chosen by backend. The memory backend is the default; adding a
        # "sql" branch here (implementing the same ports) is the only change needed to
        # run against a cloud database.
        if self.config.backend == "memory":
            self.workspaces = InMemoryWorkspaceRepository()
            self.users = InMemoryUserRepository()
            self.roles = InMemoryRoleRepository()
            self.projects = InMemoryProjectRepository()
            self.teams = InMemoryTeamRepository()
            self.api_keys = InMemoryApiKeyRepository()
            self.audit_repo = InMemoryAuditRepository()
        else:  # pragma: no cover - cloud backends are wired in deployment
            raise NotImplementedError(
                f"backend '{self.config.backend}' not bundled; implement the repository "
                "ports and wire them here (e.g. a SQL adapter using database_url)"
            )

        # Security services.
        self.tokens = TokenService(
            self.config.secret_key,
            issuer=self.config.issuer,
            ttl_seconds=self.config.token_ttl_seconds,
        )

        # Application services.
        self.audit = AuditService(self.audit_repo)
        self.authorizer = Authorizer(self.roles)
        self.auth = AuthService(self.users, self.api_keys, self.tokens, self.audit)
        self.workspace_service = WorkspaceService(
            self.workspaces, self.roles, self.users, self.audit,
            min_password_length=self.config.min_password_length,
        )
        self.user_service = UserService(
            self.users, self.roles, self.audit, min_password_length=self.config.min_password_length,
        )
        self.project_service = ProjectService(self.projects, self.audit)
        self.team_service = TeamService(self.teams, self.audit)
        self.apikey_service = ApiKeyService(self.api_keys, self.audit, prefix=self.config.api_key_prefix)


def build_container(config: EnterpriseConfig | None = None) -> EnterpriseContainer:
    return EnterpriseContainer(config)
