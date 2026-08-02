"""In-memory repository adapters.

Thread-safe reference implementations of every repository port. They are the default
backend and the substrate for tests. A cloud deployment swaps these for SQL/NoSQL
adapters implementing the same ports — no service code changes.
"""

from __future__ import annotations

import threading

from ..domain.models import ApiKey, AuditEntry, Project, Role, Team, User, Workspace


class _Base:
    def __init__(self) -> None:
        self._lock = threading.RLock()


class InMemoryWorkspaceRepository(_Base):
    def __init__(self) -> None:
        super().__init__()
        self._by_id: dict[str, Workspace] = {}

    def add(self, workspace: Workspace) -> Workspace:
        with self._lock:
            self._by_id[workspace.id] = workspace
            return workspace

    def get(self, workspace_id: str) -> Workspace | None:
        return self._by_id.get(workspace_id)

    def get_by_slug(self, slug: str) -> Workspace | None:
        return next((w for w in self._by_id.values() if w.slug == slug), None)

    def list(self) -> list[Workspace]:
        return list(self._by_id.values())


class InMemoryUserRepository(_Base):
    def __init__(self) -> None:
        super().__init__()
        self._by_id: dict[str, User] = {}

    def add(self, user: User) -> User:
        with self._lock:
            self._by_id[user.id] = user
            return user

    def get(self, user_id: str) -> User | None:
        return self._by_id.get(user_id)

    def get_by_email(self, workspace_id: str, email: str) -> User | None:
        email = email.lower()
        return next(
            (u for u in self._by_id.values() if u.workspace_id == workspace_id and u.email.lower() == email),
            None,
        )

    def list(self, workspace_id: str) -> list[User]:
        return [u for u in self._by_id.values() if u.workspace_id == workspace_id]

    def update(self, user: User) -> User:
        with self._lock:
            self._by_id[user.id] = user
            return user

    def delete(self, user_id: str) -> bool:
        with self._lock:
            return self._by_id.pop(user_id, None) is not None


class InMemoryRoleRepository(_Base):
    def __init__(self) -> None:
        super().__init__()
        self._items: dict[tuple[str, str], Role] = {}

    def add(self, role: Role) -> Role:
        with self._lock:
            self._items[(role.workspace_id, role.name)] = role
            return role

    def get(self, workspace_id: str, name: str) -> Role | None:
        return self._items.get((workspace_id, name))

    def list(self, workspace_id: str) -> list[Role]:
        return [r for (ws, _), r in self._items.items() if ws == workspace_id]

    def delete(self, workspace_id: str, name: str) -> bool:
        with self._lock:
            return self._items.pop((workspace_id, name), None) is not None


class InMemoryProjectRepository(_Base):
    def __init__(self) -> None:
        super().__init__()
        self._by_id: dict[str, Project] = {}

    def add(self, project: Project) -> Project:
        with self._lock:
            self._by_id[project.id] = project
            return project

    def get(self, project_id: str) -> Project | None:
        return self._by_id.get(project_id)

    def list(self, workspace_id: str) -> list[Project]:
        return [p for p in self._by_id.values() if p.workspace_id == workspace_id]

    def update(self, project: Project) -> Project:
        with self._lock:
            self._by_id[project.id] = project
            return project

    def delete(self, project_id: str) -> bool:
        with self._lock:
            return self._by_id.pop(project_id, None) is not None


class InMemoryTeamRepository(_Base):
    def __init__(self) -> None:
        super().__init__()
        self._by_id: dict[str, Team] = {}

    def add(self, team: Team) -> Team:
        with self._lock:
            self._by_id[team.id] = team
            return team

    def get(self, team_id: str) -> Team | None:
        return self._by_id.get(team_id)

    def list(self, workspace_id: str) -> list[Team]:
        return [t for t in self._by_id.values() if t.workspace_id == workspace_id]

    def update(self, team: Team) -> Team:
        with self._lock:
            self._by_id[team.id] = team
            return team

    def delete(self, team_id: str) -> bool:
        with self._lock:
            return self._by_id.pop(team_id, None) is not None


class InMemoryApiKeyRepository(_Base):
    def __init__(self) -> None:
        super().__init__()
        self._by_id: dict[str, ApiKey] = {}

    def add(self, key: ApiKey) -> ApiKey:
        with self._lock:
            self._by_id[key.id] = key
            return key

    def get_by_public_id(self, public_id: str) -> ApiKey | None:
        return next((k for k in self._by_id.values() if k.public_id == public_id), None)

    def list(self, workspace_id: str) -> list[ApiKey]:
        return [k for k in self._by_id.values() if k.workspace_id == workspace_id]

    def update(self, key: ApiKey) -> ApiKey:
        with self._lock:
            self._by_id[key.id] = key
            return key


class InMemoryAuditRepository(_Base):
    def __init__(self) -> None:
        super().__init__()
        self._entries: list[AuditEntry] = []

    def add(self, entry: AuditEntry) -> AuditEntry:
        with self._lock:
            self._entries.append(entry)
            return entry

    def query(
        self, workspace_id: str, *, actor_id: str | None = None, action: str | None = None, limit: int = 100
    ) -> list[AuditEntry]:
        result = [
            e
            for e in reversed(self._entries)
            if e.workspace_id == workspace_id
            and (actor_id is None or e.actor_id == actor_id)
            and (action is None or e.action == action)
        ]
        return result[:limit]
