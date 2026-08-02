"""API-key generation and verification.

A key looks like ``<prefix>_<pubid>_<secret>``. Only a hash of the whole key is stored;
the plaintext is returned once at creation and never again. Verification hashes the
presented key and compares in constant time. The ``prefix`` and public id make keys
recognisable in logs and secret managers without revealing the secret.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass


@dataclass(slots=True)
class GeneratedKey:
    plaintext: str
    prefix: str
    public_id: str
    secret_hash: str


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def generate_key(prefix: str) -> GeneratedKey:
    public_id = secrets.token_hex(4)
    secret = secrets.token_urlsafe(32)
    plaintext = f"{prefix}_{public_id}_{secret}"
    return GeneratedKey(
        plaintext=plaintext, prefix=prefix, public_id=public_id, secret_hash=_hash(plaintext)
    )


def verify_key(presented: str, secret_hash: str) -> bool:
    return hmac.compare_digest(_hash(presented), secret_hash)
