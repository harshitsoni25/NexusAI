"""Password hashing with the standard library only (scrypt, memory-hard).

Hashes are self-describing: ``scrypt$n$r$p$salt_hex$hash_hex``. Verification is constant
-time. No third-party dependency is required, which keeps the image small and the
supply chain minimal — useful for cloud deployment.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

_N = 2**14
_R = 8
_P = 1
_DKLEN = 32


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${derived.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, hash_hex = encoded.split("$")
        if scheme != "scrypt":
            return False
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(bytes.fromhex(hash_hex)),
        )
        return hmac.compare_digest(derived.hex(), hash_hex)
    except (ValueError, TypeError):
        return False
