"""End-to-end enterprise flow across services, plus a FastAPI integration smoke."""

from __future__ import annotations

import pytest

from nexusai_pro_enterprise import (
    AuthenticationError,
    ConflictError,
    build_container,
)


def _bootstrap():
    c = build_container()
    ws, owner = c.workspace_service.create_workspace(
        "Acme", "acme", owner_email="owner@acme.co", owner_password="password123"
    )
    return c, ws, owner


def test_workspace_seeds_builtin_roles_and_owner():
    c, ws, owner = _bootstrap()
    names = {r.name for r in c.roles.list(ws.id)}
    assert names == {"owner", "admin", "member", "viewer"}
    assert owner.roles == {"owner"}


def test_login_issues_token_and_authenticates():
    c, ws, _ = _bootstrap()
    token = c.auth.login(ws.id, "owner@acme.co", "password123")
    principal = c.auth.authenticate_token(token)
    assert principal.workspace_id == ws.id and "owner" in principal.roles
    with pytest.raises(AuthenticationError):
        c.auth.login(ws.id, "owner@acme.co", "wrong")


def test_full_lifecycle_users_teams_projects_apikeys_audit():
    c, ws, owner = _bootstrap()

    # users
    dev = c.user_service.create_user(
        ws.id, "dev@acme.co", "password123", roles={"member"}, actor_id=owner.id
    )
    with pytest.raises(ConflictError):
        c.user_service.create_user(ws.id, "dev@acme.co", "password123", actor_id=owner.id)
    c.user_service.set_roles(ws.id, dev.id, {"admin"}, actor_id=owner.id)
    assert c.user_service.get(dev.id).roles == {"admin"}

    # teams
    team = c.team_service.create(ws.id, "Crawlers", actor_id=owner.id)
    c.team_service.add_member(team.id, dev.id, actor_id=owner.id)
    assert dev.id in c.team_service.get(team.id).member_ids

    # projects
    project = c.project_service.create(ws.id, "Price Monitor", "PM", actor_id=owner.id)
    c.project_service.add_member(project.id, dev.id, actor_id=owner.id)
    c.project_service.assign_team(project.id, team.id, actor_id=owner.id)
    fetched = c.project_service.get(project.id)
    assert dev.id in fetched.member_ids and team.id in fetched.team_ids

    # api keys — plaintext returned once, then usable to authenticate
    created = c.apikey_service.create(ws.id, "ci-key", created_by=owner.id)
    assert created.plaintext.startswith("hk_")
    principal = c.auth.authenticate_api_key(created.plaintext)
    assert principal.workspace_id == ws.id and principal.via == "api_key"
    c.apikey_service.revoke(ws.id, created.key.id, actor_id=owner.id)
    with pytest.raises(AuthenticationError):
        c.auth.authenticate_api_key(created.plaintext)  # revoked

    # audit captured every action, newest first
    actions = [e.action for e in c.audit.query(ws.id, limit=100)]
    for expected in (
        "workspace.created",
        "user.created",
        "team.created",
        "project.created",
        "apikey.created",
        "apikey.revoked",
    ):
        assert expected in actions


def test_tenant_isolation():
    c, ws_a, owner_a = _bootstrap()
    ws_b, _ = c.workspace_service.create_workspace(
        "Beta", "beta", owner_email="o@beta.co", owner_password="password123"
    )
    c.user_service.create_user(ws_a.id, "a@acme.co", "password123", actor_id=owner_a.id)
    # workspace B cannot see workspace A's users
    assert all(u.workspace_id == ws_b.id for u in c.user_service.list(ws_b.id))
    assert "a@acme.co" not in {u.email for u in c.user_service.list(ws_b.id)}


# --- FastAPI integration smoke ---------------------------------------------


def test_api_end_to_end():
    from fastapi.testclient import TestClient

    from nexusai_pro_enterprise.app.api import create_enterprise_app

    app = create_enterprise_app()
    with TestClient(app) as client:
        # create workspace + owner
        r = client.post(
            "/api/enterprise/workspaces",
            json={
                "name": "Acme",
                "slug": "acme",
                "owner_email": "owner@acme.co",
                "owner_password": "password123",
            },
        )
        assert r.status_code == 201, r.text
        ws_id = r.json()["workspace"]["id"]

        # unauthenticated is rejected
        assert client.get("/api/enterprise/users").status_code == 401

        # login -> token
        token = client.post(
            "/api/enterprise/auth/login",
            json={"workspace_id": ws_id, "email": "owner@acme.co", "password": "password123"},
        ).json()["token"]
        auth = {"Authorization": f"Bearer {token}"}

        assert client.get("/api/enterprise/me", headers=auth).json()["roles"] == ["owner"]

        # create a user, project, team, api key
        assert (
            client.post(
                "/api/enterprise/users",
                headers=auth,
                json={"email": "dev@acme.co", "password": "password123", "roles": ["member"]},
            ).status_code
            == 201
        )
        assert (
            client.post(
                "/api/enterprise/projects", headers=auth, json={"name": "PM", "key": "PM"}
            ).status_code
            == 201
        )
        assert (
            client.post(
                "/api/enterprise/teams", headers=auth, json={"name": "Crawlers"}
            ).status_code
            == 201
        )
        key_resp = client.post("/api/enterprise/api-keys", headers=auth, json={"name": "ci"})
        assert key_resp.status_code == 201
        api_key = key_resp.json()["api_key"]

        # the API key authenticates too
        assert (
            client.get("/api/enterprise/me", headers={"X-API-Key": api_key}).json()["via"]
            == "api_key"
        )

        # audit log is populated and permission-guarded
        audit = client.get("/api/enterprise/audit", headers=auth)
        assert audit.status_code == 200 and any(e["action"] == "user.created" for e in audit.json())

        # a viewer-less member token cannot manage users (403)
        dev_token = client.post(
            "/api/enterprise/auth/login",
            json={"workspace_id": ws_id, "email": "dev@acme.co", "password": "password123"},
        ).json()["token"]
        forbidden = client.post(
            "/api/enterprise/users",
            headers={"Authorization": f"Bearer {dev_token}"},
            json={"email": "x@acme.co", "password": "password123"},
        )
        assert forbidden.status_code == 403
