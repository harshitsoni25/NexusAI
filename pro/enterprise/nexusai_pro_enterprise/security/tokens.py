"""Stateless, signed auth tokens (JWT-shaped, HMAC-SHA256, stdlib only).

Because tokens are self-contained and signed, no server-side session store is needed;
any instance can validate any token, which is what makes horizontal scaling trivial.
Tokens carry the subject, workspace, roles and expiry.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass


class TokenError(Exception):
    pass


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


@dataclass(slots=True)
class TokenClaims:
    sub: str  # user id
    ws: str  # workspace id
    email: str
    roles: list[str]
    iat: int
    exp: int
    iss: str


class TokenService:
    def __init__(self, secret: str, *, issuer: str, ttl_seconds: int) -> None:
        self._secret = secret.encode("utf-8")
        self._issuer = issuer
        self._ttl = ttl_seconds

    def issue(self, *, user_id: str, workspace_id: str, email: str, roles: list[str]) -> str:
        now = int(time.time())
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": user_id,
            "ws": workspace_id,
            "email": email,
            "roles": roles,
            "iat": now,
            "exp": now + self._ttl,
            "iss": self._issuer,
        }
        signing_input = (
            f"{_b64u(json.dumps(header).encode())}.{_b64u(json.dumps(payload).encode())}"
        )
        signature = hmac.new(self._secret, signing_input.encode(), hashlib.sha256).digest()
        return f"{signing_input}.{_b64u(signature)}"

    def verify(self, token: str) -> TokenClaims:
        try:
            header_b64, payload_b64, sig_b64 = token.split(".")
        except ValueError as exc:
            raise TokenError("malformed token") from exc

        signing_input = f"{header_b64}.{payload_b64}"
        expected = hmac.new(self._secret, signing_input.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64u_decode(sig_b64)):
            raise TokenError("bad signature")

        payload = json.loads(_b64u_decode(payload_b64))
        if payload.get("iss") != self._issuer:
            raise TokenError("wrong issuer")
        if int(payload.get("exp", 0)) < int(time.time()):
            raise TokenError("token expired")
        return TokenClaims(
            sub=payload["sub"],
            ws=payload["ws"],
            email=payload.get("email", ""),
            roles=list(payload.get("roles", [])),
            iat=int(payload["iat"]),
            exp=int(payload["exp"]),
            iss=payload["iss"],
        )
