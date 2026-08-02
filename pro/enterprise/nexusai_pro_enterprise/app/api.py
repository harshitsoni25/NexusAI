"""A standalone FastAPI application exposing the enterprise features over REST.

This app is independent of the Community engine and the existing Pro API — it can be
deployed on its own or mounted alongside them. Every mutating route is permission-
guarded and audited. It is stateless (signed tokens), so it scales horizontally behind
a load balancer; persistence is whatever the container is wired with.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, status
from pydantic import BaseModel, Field

from ..config import EnterpriseConfig
from ..domain.permissions import Permission
from ..errors import (
    AuthenticationError,
    ConflictError,
    EnterpriseError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from .container import EnterpriseContainer, build_container
from .dependencies import PrincipalDep, get_container, require

# --- request/response models ------------------------------------------------


class WorkspaceCreate(BaseModel):
    name: str
    slug: str = Field(..., description="3-40 chars, lowercase alphanumeric and hyphens")
    owner_email: str
    owner_password: str


class LoginRequest(BaseModel):
    workspace_id: str
    email: str
    password: str


class UserCreate(BaseModel):
    email: str
    password: str
    roles: list[str] = Field(default_factory=lambda: ["member"])
    display_name: str = ""


class RolesUpdate(BaseModel):
    roles: list[str]


class ProjectCreate(BaseModel):
    name: str
    key: str
    description: str = ""


class TeamCreate(BaseModel):
    name: str


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str] = Field(default_factory=list)


def create_enterprise_app(
    container: EnterpriseContainer | None = None, *, config: EnterpriseConfig | None = None
) -> FastAPI:
    container = container or build_container(config)
    app = FastAPI(title="Nexus AI Pro — Enterprise", version="0.1.0")
    app.state.enterprise = container

    # Map domain errors to HTTP.
    @app.exception_handler(EnterpriseError)
    async def _errors(_request, exc: EnterpriseError):  # type: ignore[no-untyped-def]
        from fastapi.responses import JSONResponse

        code = {
            AuthenticationError: 401,
            PermissionDenied: 403,
            NotFoundError: 404,
            ConflictError: 409,
            ValidationError: 422,
        }.get(type(exc), 400)
        return JSONResponse(
            status_code=code, content={"error": {"type": type(exc).__name__, "message": str(exc)}}
        )

    # --- auth & workspaces -------------------------------------------------

    @app.post(
        "/api/enterprise/workspaces", status_code=status.HTTP_201_CREATED, tags=["Workspaces"]
    )
    def create_workspace(
        body: WorkspaceCreate, c: EnterpriseContainer = Depends(get_container)
    ) -> dict[str, object]:
        ws, owner = c.workspace_service.create_workspace(
            body.name, body.slug, owner_email=body.owner_email, owner_password=body.owner_password
        )
        return {
            "workspace": {"id": ws.id, "slug": ws.slug, "name": ws.name},
            "owner": {"id": owner.id, "email": owner.email},
        }

    @app.post("/api/enterprise/auth/login", tags=["Auth"])
    def login(
        body: LoginRequest, c: EnterpriseContainer = Depends(get_container)
    ) -> dict[str, object]:
        token = c.auth.login(body.workspace_id, body.email, body.password)
        return {"token": token, "token_type": "bearer"}

    @app.get("/api/enterprise/me", tags=["Auth"])
    def me(principal: PrincipalDep) -> dict[str, object]:
        return {
            "user_id": principal.user_id,
            "workspace_id": principal.workspace_id,
            "email": principal.email,
            "roles": sorted(principal.roles),
            "via": principal.via,
        }

    # --- users -------------------------------------------------------------

    @app.get(
        "/api/enterprise/users",
        tags=["Users"],
        dependencies=[Depends(require(Permission.USER_READ))],
    )
    def list_users(
        principal: PrincipalDep, c: EnterpriseContainer = Depends(get_container)
    ) -> list[dict[str, object]]:
        return [
            {"id": u.id, "email": u.email, "roles": sorted(u.roles), "active": u.active}
            for u in c.user_service.list(principal.workspace_id)
        ]

    @app.post(
        "/api/enterprise/users",
        status_code=201,
        tags=["Users"],
        dependencies=[Depends(require(Permission.USER_MANAGE))],
    )
    def create_user(
        body: UserCreate, principal: PrincipalDep, c: EnterpriseContainer = Depends(get_container)
    ) -> dict[str, object]:
        u = c.user_service.create_user(
            principal.workspace_id,
            body.email,
            body.password,
            roles=set(body.roles),
            display_name=body.display_name,
            actor_id=principal.user_id,
        )
        return {"id": u.id, "email": u.email, "roles": sorted(u.roles)}

    @app.put(
        "/api/enterprise/users/{user_id}/roles",
        tags=["Users"],
        dependencies=[Depends(require(Permission.ROLE_MANAGE))],
    )
    def set_user_roles(
        user_id: str,
        body: RolesUpdate,
        principal: PrincipalDep,
        c: EnterpriseContainer = Depends(get_container),
    ) -> dict[str, object]:
        u = c.user_service.set_roles(
            principal.workspace_id, user_id, set(body.roles), actor_id=principal.user_id
        )
        return {"id": u.id, "roles": sorted(u.roles)}

    # --- roles -------------------------------------------------------------

    @app.get(
        "/api/enterprise/roles",
        tags=["Roles"],
        dependencies=[Depends(require(Permission.WORKSPACE_READ))],
    )
    def list_roles(
        principal: PrincipalDep, c: EnterpriseContainer = Depends(get_container)
    ) -> list[dict[str, object]]:
        return [
            {"name": r.name, "permissions": sorted(r.permissions), "builtin": r.builtin}
            for r in c.roles.list(principal.workspace_id)
        ]

    # --- projects ----------------------------------------------------------

    @app.get(
        "/api/enterprise/projects",
        tags=["Projects"],
        dependencies=[Depends(require(Permission.PROJECT_READ))],
    )
    def list_projects(
        principal: PrincipalDep, c: EnterpriseContainer = Depends(get_container)
    ) -> list[dict[str, object]]:
        return [
            {
                "id": p.id,
                "name": p.name,
                "key": p.key,
                "members": len(p.member_ids),
                "teams": len(p.team_ids),
            }
            for p in c.project_service.list(principal.workspace_id)
        ]

    @app.post(
        "/api/enterprise/projects",
        status_code=201,
        tags=["Projects"],
        dependencies=[Depends(require(Permission.PROJECT_MANAGE))],
    )
    def create_project(
        body: ProjectCreate,
        principal: PrincipalDep,
        c: EnterpriseContainer = Depends(get_container),
    ) -> dict[str, object]:
        p = c.project_service.create(
            principal.workspace_id,
            body.name,
            body.key,
            description=body.description,
            actor_id=principal.user_id,
        )
        return {"id": p.id, "name": p.name, "key": p.key}

    # --- teams -------------------------------------------------------------

    @app.get(
        "/api/enterprise/teams",
        tags=["Teams"],
        dependencies=[Depends(require(Permission.TEAM_READ))],
    )
    def list_teams(
        principal: PrincipalDep, c: EnterpriseContainer = Depends(get_container)
    ) -> list[dict[str, object]]:
        return [
            {"id": t.id, "name": t.name, "members": len(t.member_ids)}
            for t in c.team_service.list(principal.workspace_id)
        ]

    @app.post(
        "/api/enterprise/teams",
        status_code=201,
        tags=["Teams"],
        dependencies=[Depends(require(Permission.TEAM_MANAGE))],
    )
    def create_team(
        body: TeamCreate, principal: PrincipalDep, c: EnterpriseContainer = Depends(get_container)
    ) -> dict[str, object]:
        t = c.team_service.create(principal.workspace_id, body.name, actor_id=principal.user_id)
        return {"id": t.id, "name": t.name}

    # --- API keys ----------------------------------------------------------

    @app.get(
        "/api/enterprise/api-keys",
        tags=["API Keys"],
        dependencies=[Depends(require(Permission.APIKEY_MANAGE))],
    )
    def list_api_keys(
        principal: PrincipalDep, c: EnterpriseContainer = Depends(get_container)
    ) -> list[dict[str, object]]:
        return [
            {
                "id": k.id,
                "name": k.name,
                "public_id": k.public_id,
                "active": k.active,
                "created_at": k.created_at.isoformat(),
            }
            for k in c.apikey_service.list(principal.workspace_id)
        ]

    @app.post(
        "/api/enterprise/api-keys",
        status_code=201,
        tags=["API Keys"],
        dependencies=[Depends(require(Permission.APIKEY_MANAGE))],
    )
    def create_api_key(
        body: ApiKeyCreate, principal: PrincipalDep, c: EnterpriseContainer = Depends(get_container)
    ) -> dict[str, object]:
        created = c.apikey_service.create(
            principal.workspace_id, body.name, created_by=principal.user_id, scopes=set(body.scopes)
        )
        # The plaintext is returned exactly once.
        return {
            "id": created.key.id,
            "name": created.key.name,
            "api_key": created.plaintext,
            "note": "store this now; it will not be shown again",
        }

    @app.delete(
        "/api/enterprise/api-keys/{key_id}",
        tags=["API Keys"],
        dependencies=[Depends(require(Permission.APIKEY_MANAGE))],
    )
    def revoke_api_key(
        key_id: str, principal: PrincipalDep, c: EnterpriseContainer = Depends(get_container)
    ) -> dict[str, object]:
        k = c.apikey_service.revoke(principal.workspace_id, key_id, actor_id=principal.user_id)
        return {"id": k.id, "active": k.active}

    # --- audit -------------------------------------------------------------

    @app.get(
        "/api/enterprise/audit",
        tags=["Audit"],
        dependencies=[Depends(require(Permission.AUDIT_READ))],
    )
    def audit_log(
        principal: PrincipalDep,
        action: str | None = None,
        limit: int = 100,
        c: EnterpriseContainer = Depends(get_container),
    ) -> list[dict[str, object]]:
        return [
            e.to_dict() for e in c.audit.query(principal.workspace_id, action=action, limit=limit)
        ]

    return app
