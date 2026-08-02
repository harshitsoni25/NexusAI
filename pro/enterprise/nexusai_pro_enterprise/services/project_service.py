"""Project management: create/list, member and team assignment."""

from __future__ import annotations

from ..domain.models import Project
from ..errors import NotFoundError
from ..ports.repositories import ProjectRepository
from .audit_service import AuditService


class ProjectService:
    def __init__(self, projects: ProjectRepository, audit: AuditService) -> None:
        self._projects = projects
        self._audit = audit

    def create(
        self, workspace_id: str, name: str, key: str, *, description: str = "", actor_id: str
    ) -> Project:
        project = self._projects.add(
            Project(workspace_id=workspace_id, name=name, key=key, description=description)
        )
        self._audit.record(
            workspace_id,
            "project.created",
            actor_id=actor_id,
            target_type="project",
            target_id=project.id,
        )
        return project

    def get(self, project_id: str) -> Project:
        project = self._projects.get(project_id)
        if project is None:
            raise NotFoundError("project not found")
        return project

    def list(self, workspace_id: str) -> list[Project]:
        return self._projects.list(workspace_id)

    def add_member(self, project_id: str, user_id: str, *, actor_id: str) -> Project:
        project = self.get(project_id)
        project.member_ids.add(user_id)
        self._projects.update(project)
        self._audit.record(
            project.workspace_id,
            "project.member_added",
            actor_id=actor_id,
            target_id=project_id,
            metadata={"user": user_id},
        )
        return project

    def assign_team(self, project_id: str, team_id: str, *, actor_id: str) -> Project:
        project = self.get(project_id)
        project.team_ids.add(team_id)
        self._projects.update(project)
        self._audit.record(
            project.workspace_id,
            "project.team_assigned",
            actor_id=actor_id,
            target_id=project_id,
            metadata={"team": team_id},
        )
        return project
