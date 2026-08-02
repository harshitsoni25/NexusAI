"""Authentication: turning credentials into a verified ``Principal``.

Two mechanisms are supported, both stateless at the edge:
  * password login issues a signed token (for interactive users);
  * an API key authenticates machine callers.

Both resolve to the same ``Principal`` so downstream authorization is identical.
"""

from __future__ import annotations

from ..domain.models import Principal, User
from ..errors import AuthenticationError
from ..ports.repositories import ApiKeyRepository, UserRepository
from ..security.apikeys import verify_key
from ..security.passwords import verify_password
from ..security.tokens import TokenError, TokenService
from .audit_service import AuditService


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        api_keys: ApiKeyRepository,
        tokens: TokenService,
        audit: AuditService,
    ) -> None:
        self._users = users
        self._api_keys = api_keys
        self._tokens = tokens
        self._audit = audit

    # --- password login ---------------------------------------------------

    def login(self, workspace_id: str, email: str, password: str) -> str:
        user = self._users.get_by_email(workspace_id, email)
        if user is None or not user.active or not verify_password(password, user.password_hash):
            self._audit.record(workspace_id, "auth.login_failed", metadata={"email": email})
            raise AuthenticationError("invalid credentials")
        self._audit.record(workspace_id, "auth.login", actor_id=user.id)
        return self._issue(user)

    def _issue(self, user: User) -> str:
        return self._tokens.issue(
            user_id=user.id,
            workspace_id=user.workspace_id,
            email=user.email,
            roles=sorted(user.roles),
        )

    # --- token authentication --------------------------------------------

    def authenticate_token(self, token: str) -> Principal:
        try:
            claims = self._tokens.verify(token)
        except TokenError as exc:
            raise AuthenticationError(str(exc)) from exc
        user = self._users.get(claims.sub)
        if user is None or not user.active:
            raise AuthenticationError("user no longer active")
        return Principal(
            user_id=user.id,
            workspace_id=user.workspace_id,
            email=user.email,
            roles=frozenset(user.roles),
            via="token",
        )

    # --- API-key authentication ------------------------------------------

    def authenticate_api_key(self, presented: str) -> Principal:
        parts = presented.split("_")
        if len(parts) < 3:
            raise AuthenticationError("malformed API key")
        public_id = parts[1]
        record = self._api_keys.get_by_public_id(public_id)
        if record is None or not record.active or not verify_key(presented, record.secret_hash):
            raise AuthenticationError("invalid API key")
        # An API key acts on behalf of its creator's roles (a service identity).
        creator = self._users.get(record.created_by)
        roles = frozenset(creator.roles) if creator else frozenset({"member"})
        return Principal(
            user_id=record.created_by,
            workspace_id=record.workspace_id,
            email=creator.email if creator else "api-key",
            roles=roles,
            via="api_key",
        )
