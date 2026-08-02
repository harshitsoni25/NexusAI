"""Security: export and report output neutralise injection payloads."""

from __future__ import annotations

import pytest

from nexusai.infrastructure.export.sanitize import neutralise

pytestmark = pytest.mark.security


class TestFormulaInjection:
    @pytest.mark.parametrize("payload", ["=1+1", "+1", "-1", "@SUM(A1)", "\tcmd", "\rcmd"])
    def test_dangerous_prefixes_are_neutralised(self, payload: str) -> None:
        result = neutralise(payload)
        assert not result.startswith(("=", "+", "-", "@", "\t", "\r"))

    def test_formula_value_is_prefixed_not_dropped(self) -> None:
        result = neutralise('=HYPERLINK("http://x")')
        assert "HYPERLINK" in result  # content preserved, execution defused

    @pytest.mark.parametrize("safe", ["Item 1", "9.99", "hello world", ""])
    def test_safe_values_unchanged(self, safe: str) -> None:
        assert neutralise(safe) == safe
