"""Team management: create/list and membership."""

from __future__ import annotations

from ..domain.models import Team
from ..errors import NotFoundError
from ..ports.repositories import TeamRepository
from .audit_service import AuditService


class TeamService:
    def __init__(self, teams: TeamRepository, audit: AuditService) -> None:
        self._teams = teams
        self._audit = audit

    def create(self, workspace_id: str, name: str, *, actor_id: str) -> Team:
        team = self._teams.add(Team(workspace_id=workspace_id, name=name))
        self._audit.record(
            workspace_id, "team.created", actor_id=actor_id, target_type="team", target_id=team.id
        )
        return team

    def get(self, team_id: str) -> Team:
        team = self._teams.get(team_id)
        if team is None:
            raise NotFoundError("team not found")
        return team

    def list(self, workspace_id: str) -> list[Team]:
        return self._teams.list(workspace_id)

    def add_member(self, team_id: str, user_id: str, *, actor_id: str) -> Team:
        team = self.get(team_id)
        team.member_ids.add(user_id)
        self._teams.update(team)
        self._audit.record(
            team.workspace_id,
            "team.member_added",
            actor_id=actor_id,
            target_id=team_id,
            metadata={"user": user_id},
        )
        return team

    def remove_member(self, team_id: str, user_id: str, *, actor_id: str) -> Team:
        team = self.get(team_id)
        team.member_ids.discard(user_id)
        self._teams.update(team)
        self._audit.record(
            team.workspace_id,
            "team.member_removed",
            actor_id=actor_id,
            target_id=team_id,
            metadata={"user": user_id},
        )
        return team
