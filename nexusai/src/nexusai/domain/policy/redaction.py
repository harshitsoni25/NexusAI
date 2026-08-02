"""Pure secret-redaction policy.

Reports and manifests carry configuration snapshots, and those snapshots may
contain secrets -- API keys, passwords, tokens. Deciding which keys are sensitive
is a policy, kept pure here so it can be audited and tested without touching a
report renderer. The policy rewrites a mapping, replacing the values of
secret-looking keys with a placeholder while leaving structure and non-secret
values intact.

It matches on the key name, not the value, because a value cannot be reliably
recognised as a secret but a key named ``password`` always names one. Matching is
substring and case-insensitive, so ``DB_PASSWORD`` and ``apiKey`` are both
caught.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from nexusai.shared.types import JsonValue

_DEFAULT_SECRET_MARKERS: tuple[str, ...] = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "credential",
    "private_key",
    "access_key",
    "auth",
)

REDACTED = "***REDACTED***"


@dataclass(frozen=True, slots=True)
class SecretRedactor:
    """Redacts the values of secret-looking keys in a mapping.

    Args:
        markers: Substrings that mark a key as secret. A key containing any of
            them, case-insensitively, has its value replaced.
    """

    markers: Sequence[str] = field(default=_DEFAULT_SECRET_MARKERS)

    def is_secret_key(self, key: str) -> bool:
        """Whether ``key`` names a secret and should have its value redacted."""
        lowered = key.lower()
        return any(marker in lowered for marker in self.markers)

    def redact(self, data: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
        """Return a copy of ``data`` with secret values replaced.

        Nested mappings and lists are redacted recursively, so a secret buried in
        a nested configuration section is caught too.
        """
        return {key: self._redact_value(key, value) for key, value in data.items()}

    def _redact_value(self, key: str, value: JsonValue) -> JsonValue:
        if self.is_secret_key(key):
            return REDACTED
        if isinstance(value, Mapping):
            return self.redact(value)
        if isinstance(value, list):
            return [self.redact(item) if isinstance(item, Mapping) else item for item in value]
        return value
