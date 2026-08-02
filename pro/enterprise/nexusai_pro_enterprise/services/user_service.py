"""User management within a workspace: create, list, roles, enable/disable, delete."""

from __future__ import annotations

from ..domain.models import User
from ..errors import ConflictError, NotFoundError, ValidationError
from ..ports.repositories import RoleRepository, UserRepository
from ..security.passwords import hash_password
from .audit_service import AuditService


class UserService:
    def __init__(
        self,
        users: UserRepository,
        roles: RoleRepository,
        audit: AuditService,
        *,
        min_password_length: int = 10,
    ) -> None:
        self._users = users
        self._roles = roles
        self._audit = audit
        self._min_pw = min_password_length

    def create_user(
        self,
        workspace_id: str,
        email: str,
        password: str,
        *,
        roles: set[str] | None = None,
        display_name: str = "",
        actor_id: str | None = None,
    ) -> User:
        if len(password) < self._min_pw:
            raise ValidationError(f"password must be at least {self._min_pw} characters")
        if self._users.get_by_email(workspace_id, email):
            raise ConflictError(f"a user with email '{email}' already exists")
        for role_name in roles or {"member"}:
            if self._roles.get(workspace_id, role_name) is None:
                raise ValidationError(f"unknown role: {role_name}")
        user = self._users.add(
            User(
                workspace_id=workspace_id,
                email=email.lower(),
                password_hash=hash_password(password),
                display_name=display_name or email.split("@")[0],
                roles=set(roles or {"member"}),
            )
        )
        self._audit.record(workspace_id, "user.created", actor_id=actor_id, target_type="user", target_id=user.id)
        return user

    def get(self, user_id: str) -> User:
        user = self._users.get(user_id)
        if user is None:
            raise NotFoundError("user not found")
        return user

    def list(self, workspace_id: str) -> list[User]:
        return self._users.list(workspace_id)

    def set_roles(self, workspace_id: str, user_id: str, roles: set[str], *, actor_id: str) -> User:
        for role_name in roles:
            if self._roles.get(workspace_id, role_name) is None:
                raise ValidationError(f"unknown role: {role_name}")
        user = self.get(user_id)
        user.roles = set(roles)
        self._users.update(user)
        self._audit.record(workspace_id, "user.roles_changed", actor_id=actor_id, target_id=user_id, metadata={"roles": ",".join(sorted(roles))})
        return user

    def set_active(self, workspace_id: str, user_id: str, active: bool, *, actor_id: str) -> User:
        user = self.get(user_id)
        user.active = active
        self._users.update(user)
        self._audit.record(workspace_id, "user.enabled" if active else "user.disabled", actor_id=actor_id, target_id=user_id)
        return user

    def delete(self, workspace_id: str, user_id: str, *, actor_id: str) -> bool:
        ok = self._users.delete(user_id)
        if ok:
            self._audit.record(workspace_id, "user.deleted", actor_id=actor_id, target_id=user_id)
        return ok
