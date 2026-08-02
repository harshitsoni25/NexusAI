"""Security: synthetic secrets never survive redaction into snapshots or logs."""

from __future__ import annotations

import pytest

from nexusai.domain.policy.redaction import SecretRedactor

pytestmark = pytest.mark.security

_SECRET = "hunter2-SYNTHETIC-do-not-log"


class TestRedaction:
    @pytest.mark.parametrize(
        "key", ["password", "api_key", "authorization", "token", "secret", "DB_PASSWORD"]
    )
    def test_secret_keys_are_redacted(self, key: str) -> None:
        result = SecretRedactor().redact({key: _SECRET})
        assert _SECRET not in str(result[key])

    def test_nested_secret_is_redacted(self) -> None:
        data = {"db": {"host": "localhost", "password": _SECRET}}
        result = SecretRedactor().redact(data)
        assert _SECRET not in str(result)
        db = result["db"]
        assert isinstance(db, dict)
        assert db["host"] == "localhost"

    def test_non_secret_values_preserved(self) -> None:
        result = SecretRedactor().redact({"host": "localhost", "port": 5432})
        assert result == {"host": "localhost", "port": 5432}

    def test_secret_in_list_of_mappings_redacted(self) -> None:
        data = {"items": [{"token": _SECRET}, {"name": "ok"}]}
        result = SecretRedactor().redact(data)
        assert _SECRET not in str(result)
