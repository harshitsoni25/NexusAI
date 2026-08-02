"""Password hashing, stateless tokens, and API-key generation/verification."""

from __future__ import annotations

import time

import pytest

from nexusai_pro_enterprise.security.apikeys import generate_key, verify_key
from nexusai_pro_enterprise.security.passwords import hash_password, verify_password
from nexusai_pro_enterprise.security.tokens import TokenError, TokenService


def test_password_hash_roundtrip():
    h = hash_password("correct horse battery")
    assert h.startswith("scrypt$")
    assert verify_password("correct horse battery", h)
    assert not verify_password("wrong", h)


def test_password_hashes_are_salted():
    assert hash_password("same") != hash_password("same")  # random salt


def test_token_issue_and_verify():
    svc = TokenService("secret", issuer="hk", ttl_seconds=60)
    token = svc.issue(user_id="u1", workspace_id="w1", email="a@b.c", roles=["admin"])
    claims = svc.verify(token)
    assert claims.sub == "u1" and claims.ws == "w1" and "admin" in claims.roles


def test_token_rejects_tampering_and_expiry():
    svc = TokenService("secret", issuer="hk", ttl_seconds=60)
    token = svc.issue(user_id="u1", workspace_id="w1", email="a@b.c", roles=[])
    with pytest.raises(TokenError):
        svc.verify(token + "x")  # bad signature
    with pytest.raises(TokenError):
        TokenService("other-secret", issuer="hk", ttl_seconds=60).verify(token)  # wrong key

    expired = TokenService("secret", issuer="hk", ttl_seconds=-1)
    t2 = expired.issue(user_id="u", workspace_id="w", email="", roles=[])
    time.sleep(0.01)
    with pytest.raises(TokenError):
        svc.verify(t2)


def test_api_key_generation_and_verification():
    g = generate_key("hk")
    assert g.plaintext.startswith("hk_")
    assert verify_key(g.plaintext, g.secret_hash)
    assert not verify_key("hk_deadbeef_wrong", g.secret_hash)
