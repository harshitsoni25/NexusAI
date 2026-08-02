"""Enterprise domain entities.

Everything is scoped to a ``Workspace`` (the tenant boundary): users belong to a
workspace, and projects, teams, API keys and audit entries all carry a ``workspace_id``.
The models are plain dataclasses so any persistence backend can map them.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class Workspace:
    """A tenant. The top-level isolation boundary for all other entities."""

    name: str
    slug: str
    id: str = field(default_factory=lambda: _uid("ws"))
    created_at: datetime = field(default_factory=_now)
    settings: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class User:
    """An account within a workspace, with hashed credentials and assigned roles."""

    workspace_id: str
    email: str
    password_hash: str
    display_name: str = ""
    roles: set[str] = field(default_factory=lambda: {"member"})
    active: bool = True
    id: str = field(default_factory=lambda: _uid("usr"))
    created_at: datetime = field(default_factory=_now)


@dataclass(slots=True)
class Role:
    """A named bundle of permissions. Built-in roles are seeded per workspace."""

    workspace_id: str
    name: str
    permissions: set[str]
    builtin: bool = False
    id: str = field(default_factory=lambda: _uid("role"))


@dataclass(slots=True)
class Project:
    """A unit of work within a workspace, with direct member users and assigned teams."""

    workspace_id: str
    name: str
    key: str
    description: str = ""
    member_ids: set[str] = field(default_factory=set)
    team_ids: set[str] = field(default_factory=set)
    id: str = field(default_factory=lambda: _uid("prj"))
    created_at: datetime = field(default_factory=_now)


@dataclass(slots=True)
class Team:
    """A group of users within a workspace that can be granted access collectively."""

    workspace_id: str
    name: str
    member_ids: set[str] = field(default_factory=set)
    id: str = field(default_factory=lambda: _uid("team"))
    created_at: datetime = field(default_factory=_now)


@dataclass(slots=True)
class ApiKey:
    """A workspace-scoped credential. Only the hash is stored; the secret is shown once."""

    workspace_id: str
    name: str
    prefix: str
    public_id: str
    secret_hash: str
    created_by: str
    scopes: set[str] = field(default_factory=set)
    active: bool = True
    id: str = field(default_factory=lambda: _uid("key"))
    created_at: datetime = field(default_factory=_now)
    last_used_at: datetime | None = None


@dataclass(slots=True)
class AuditEntry:
    """An append-only record of a security- or data-relevant action."""

    workspace_id: str
    action: str
    actor_id: str | None
    target_type: str | None = None
    target_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    id: str = field(default_factory=lambda: _uid("aud"))
    at: datetime = field(default_factory=_now)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "action": self.action,
            "actor_id": self.actor_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "metadata": self.metadata,
            "at": self.at.isoformat(),
        }


@dataclass(slots=True)
class Principal:
    """The authenticated subject of a request, carrying its workspace and roles."""

    user_id: str
    workspace_id: str
    email: str
    roles: frozenset[str]
    via: str = "token"  # "token" | "api_key"

    def has_role(self, role: str) -> bool:
        return role in self.roles
