"""Nexus AI Pro — Enterprise layer.

Multi-tenant authentication, users, roles (RBAC), projects, teams, API keys, audit logs
and workspace management, built cloud-ready (stateless tokens, pluggable persistence,
12-factor config). It is an additive Pro layer: the Community engine is not modified.
"""

from .app.container import EnterpriseContainer, build_container
from .config import EnterpriseConfig
from .domain.models import (
    ApiKey,
    AuditEntry,
    Principal,
    Project,
    Role,
    Team,
    User,
    Workspace,
)
from .domain.permissions import BUILTIN_ROLES, Permission
from .errors import (
    AuthenticationError,
    ConflictError,
    EnterpriseError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)

__all__ = [
    "EnterpriseConfig",
    "EnterpriseContainer",
    "build_container",
    "Permission",
    "BUILTIN_ROLES",
    "Workspace",
    "User",
    "Role",
    "Project",
    "Team",
    "ApiKey",
    "AuditEntry",
    "Principal",
    "EnterpriseError",
    "AuthenticationError",
    "PermissionDenied",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
]
