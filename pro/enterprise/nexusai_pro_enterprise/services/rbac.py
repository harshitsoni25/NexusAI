"""Authorization: does a principal hold a permission in its workspace?"""

from __future__ import annotations

from ..domain.models import Principal
from ..domain.permissions import Permission
from ..errors import PermissionDenied
from ..ports.repositories import RoleRepository


class Authorizer:
    """Resolves a principal's roles to permissions and enforces checks."""

    def __init__(self, roles: RoleRepository) -> None:
        self._roles = roles

    def permissions_for(self, principal: Principal) -> set[str]:
        granted: set[str] = set()
        for role_name in principal.roles:
            role = self._roles.get(principal.workspace_id, role_name)
            if role:
                granted |= set(role.permissions)
        return granted

    def has(self, principal: Principal, permission: Permission) -> bool:
        return permission.value in self.permissions_for(principal)

    def require(self, principal: Principal, permission: Permission) -> None:
        if not self.has(principal, permission):
            raise PermissionDenied(f"missing permission: {permission.value}")
