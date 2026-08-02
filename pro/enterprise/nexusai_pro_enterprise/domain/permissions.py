"""Permissions and the built-in role model.

Authorization is permission-based. Roles are named bundles of permissions; a principal
holds one or more roles within a workspace, and a check passes when any of the
principal's roles grants the required permission. The built-in roles cover the common
tenancy shape (owner / admin / member / viewer); custom roles can be added per
workspace with any subset of permissions.
"""

from __future__ import annotations

from enum import Enum


class Permission(str, Enum):
    # workspace / tenancy
    WORKSPACE_MANAGE = "workspace:manage"
    WORKSPACE_READ = "workspace:read"
    # identity & access
    USER_MANAGE = "user:manage"
    USER_READ = "user:read"
    ROLE_MANAGE = "role:manage"
    APIKEY_MANAGE = "apikey:manage"
    # collaboration
    PROJECT_MANAGE = "project:manage"
    PROJECT_WRITE = "project:write"
    PROJECT_READ = "project:read"
    TEAM_MANAGE = "team:manage"
    TEAM_READ = "team:read"
    # operations
    SCRAPE_RUN = "scrape:run"
    AUDIT_READ = "audit:read"


# Built-in roles. OWNER implicitly holds every permission (see role_permissions()).
BUILTIN_ROLES: dict[str, frozenset[Permission]] = {
    "owner": frozenset(Permission),  # everything
    "admin": frozenset(
        {
            Permission.WORKSPACE_READ,
            Permission.USER_MANAGE,
            Permission.USER_READ,
            Permission.ROLE_MANAGE,
            Permission.APIKEY_MANAGE,
            Permission.PROJECT_MANAGE,
            Permission.PROJECT_WRITE,
            Permission.PROJECT_READ,
            Permission.TEAM_MANAGE,
            Permission.TEAM_READ,
            Permission.SCRAPE_RUN,
            Permission.AUDIT_READ,
        }
    ),
    "member": frozenset(
        {
            Permission.WORKSPACE_READ,
            Permission.USER_READ,
            Permission.PROJECT_WRITE,
            Permission.PROJECT_READ,
            Permission.TEAM_READ,
            Permission.SCRAPE_RUN,
        }
    ),
    "viewer": frozenset(
        {
            Permission.WORKSPACE_READ,
            Permission.USER_READ,
            Permission.PROJECT_READ,
            Permission.TEAM_READ,
        }
    ),
}


def is_builtin(role_name: str) -> bool:
    return role_name in BUILTIN_ROLES
