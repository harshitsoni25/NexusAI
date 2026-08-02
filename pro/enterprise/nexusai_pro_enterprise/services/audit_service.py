"""Audit logging: append-only records of who did what, and querying them."""

from __future__ import annotations

from ..domain.models import AuditEntry
from ..ports.repositories import AuditRepository


class AuditService:
    def __init__(self, repo: AuditRepository) -> None:
        self._repo = repo

    def record(
        self,
        workspace_id: str,
        action: str,
        *,
        actor_id: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> AuditEntry:
        return self._repo.add(
            AuditEntry(
                workspace_id=workspace_id,
                action=action,
                actor_id=actor_id,
                target_type=target_type,
                target_id=target_id,
                metadata=metadata or {},
            )
        )

    def query(
        self,
        workspace_id: str,
        *,
        actor_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        return self._repo.query(workspace_id, actor_id=actor_id, action=action, limit=limit)
