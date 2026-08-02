"""Content hashing for artefact integrity.

Integrity checks use SHA-256 -- a cryptographic hash -- rather than a fast
non-cryptographic checksum, because the point is to detect modification,
including deliberate modification, not merely accidental corruption. The same
hash serves double duty as a duplicate detector: two artefacts with the same
SHA-256 are the same bytes.
"""

from __future__ import annotations

import hashlib

_ALGORITHM = "sha256"


def content_hash(data: bytes) -> str:
    """Return the SHA-256 hex digest of ``data``, prefixed with the algorithm."""
    digest = hashlib.sha256(data).hexdigest()
    return f"{_ALGORITHM}:{digest}"


def verify_hash(data: bytes, expected: str) -> bool:
    """Whether ``data`` hashes to ``expected``."""
    return content_hash(data) == expected
