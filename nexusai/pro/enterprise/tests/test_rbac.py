"""Role -> permission resolution and enforcement."""

from __future__ import annotations

import pytest

from nexusai_pro_enterprise import Permission, build_container
from nexusai_pro_enterprise.domain.models import Principal
from nexusai_pro_enterprise.errors import PermissionDenied


def _ctx():
    c = build_container()
    ws, owner = c.workspace_service.create_workspace("Acme", "acme", owner_email="o@acme.co", owner_password="password123")
    return c, ws, owner


def _principal(ws_id, roles):
    return Principal(user_id="u", workspace_id=ws_id, email="x@y.z", roles=frozenset(roles))


def test_owner_has_everything():
    c, ws, _ = _ctx()
    p = _principal(ws.id, {"owner"})
    for perm in Permission:
        assert c.authorizer.has(p, perm)


def test_viewer_is_read_only():
    c, ws, _ = _ctx()
    p = _principal(ws.id, {"viewer"})
    assert c.authorizer.has(p, Permission.PROJECT_READ)
    assert not c.authorizer.has(p, Permission.PROJECT_MANAGE)
    with pytest.raises(PermissionDenied):
        c.authorizer.require(p, Permission.USER_MANAGE)


def test_member_can_run_but_not_manage_users():
    c, ws, _ = _ctx()
    p = _principal(ws.id, {"member"})
    assert c.authorizer.has(p, Permission.SCRAPE_RUN)
    assert not c.authorizer.has(p, Permission.USER_MANAGE)
