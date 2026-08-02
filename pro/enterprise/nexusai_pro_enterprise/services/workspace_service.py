"""Workspace (tenant) management.

Creating a workspace seeds the built-in roles for that tenant and provisions its first
user as the owner. Everything else in the system is created inside a workspace, so this
is the entry point to a tenant.
"""

from __future__ import annotations

import re

from ..domain.models import Role, User, Workspace
from ..domain.permissions import BUILTIN_ROLES
from ..errors import ConflictError, NotFoundError, ValidationError
from ..ports.repositories import RoleRepository, UserRepository, WorkspaceRepository
from ..security.passwords import hash_password
from .audit_service import AuditService

_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")


class WorkspaceService:
    def __init__(
        self,
        workspaces: WorkspaceRepository,
        roles: RoleRepository,
        users: UserRepository,
        audit: AuditService,
        *,
        min_password_length: int = 10,
    ) -> None:
        self._workspaces = workspaces
        self._roles = roles
        self._users = users
        self._audit = audit
        self._min_pw = min_password_length

    def create_workspace(
        self, name: str, slug: str, *, owner_email: str, owner_password: str
    ) -> tuple[Workspace, User]:
        if not _SLUG.match(slug):
            raise ValidationError("slug must be 3-40 chars, lowercase alphanumeric and hyphens")
        if self._workspaces.get_by_slug(slug):
            raise ConflictError(f"workspace slug '{slug}' is taken")
        if len(owner_password) < self._min_pw:
            raise ValidationError(f"password must be at least {self._min_pw} characters")

        workspace = self._workspaces.add(Workspace(name=name, slug=slug))
        self._seed_roles(workspace.id)

        owner = self._users.add(
            User(
                workspace_id=workspace.id,
                email=owner_email.lower(),
                password_hash=hash_password(owner_password),
                display_name=owner_email.split("@")[0],
                roles={"owner"},
            )
        )
        self._audit.record(
            workspace.id,
            "workspace.created",
            actor_id=owner.id,
            target_type="workspace",
            target_id=workspace.id,
        )
        return workspace, owner

    def _seed_roles(self, workspace_id: str) -> None:
        for name, permissions in BUILTIN_ROLES.items():
            self._roles.add(
                Role(
                    workspace_id=workspace_id,
                    name=name,
                    permissions={p.value for p in permissions},
                    builtin=True,
                )
            )

    def get(self, workspace_id: str) -> Workspace:
        workspace = self._workspaces.get(workspace_id)
        if workspace is None:
            raise NotFoundError("workspace not found")
        return workspace

    def list(self) -> list[Workspace]:
        return self._workspaces.list()

    def update_settings(
        self, workspace_id: str, settings: dict[str, str], *, actor_id: str
    ) -> Workspace:
        workspace = self.get(workspace_id)
        workspace.settings.update(settings)
        self._workspaces.add(workspace)
        self._audit.record(
            workspace_id, "workspace.settings_updated", actor_id=actor_id, target_id=workspace_id
        )
        return workspace
