"""API-key management.

Creating a key returns the plaintext exactly once; only its hash and a public id are
persisted. Listing never exposes secrets. Revoking deactivates a key without deleting
its audit trail.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.models import ApiKey
from ..errors import NotFoundError
from ..ports.repositories import ApiKeyRepository
from ..security.apikeys import generate_key
from .audit_service import AuditService


@dataclass(slots=True)
class CreatedApiKey:
    """The one-time reveal of a newly created key."""

    key: ApiKey
    plaintext: str


class ApiKeyService:
    def __init__(self, api_keys: ApiKeyRepository, audit: AuditService, *, prefix: str = "hk") -> None:
        self._api_keys = api_keys
        self._audit = audit
        self._prefix = prefix

    def create(self, workspace_id: str, name: str, *, created_by: str, scopes: set[str] | None = None) -> CreatedApiKey:
        generated = generate_key(self._prefix)
        record = self._api_keys.add(
            ApiKey(
                workspace_id=workspace_id,
                name=name,
                prefix=generated.prefix,
                public_id=generated.public_id,
                secret_hash=generated.secret_hash,
                created_by=created_by,
                scopes=set(scopes or set()),
            )
        )
        self._audit.record(workspace_id, "apikey.created", actor_id=created_by, target_type="apikey", target_id=record.id)
        return CreatedApiKey(key=record, plaintext=generated.plaintext)

    def list(self, workspace_id: str) -> list[ApiKey]:
        return self._api_keys.list(workspace_id)

    def revoke(self, workspace_id: str, key_id: str, *, actor_id: str) -> ApiKey:
        record = next((k for k in self._api_keys.list(workspace_id) if k.id == key_id), None)
        if record is None:
            raise NotFoundError("api key not found")
        record.active = False
        self._api_keys.update(record)
        self._audit.record(workspace_id, "apikey.revoked", actor_id=actor_id, target_id=key_id)
        return record
