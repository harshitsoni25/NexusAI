"""Security: dangerous URLs, schemes and identifiers are rejected at the boundary."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from nexusai.presentation.cli.app import app
from nexusai.presentation.cli.exit_codes import ExitCode

pytestmark = pytest.mark.security


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def isolated_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXUSAI_PATHS__ROOT", str(tmp_path / "hk"))


class TestUrlScheme:
    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "ftp://example.com/x",
            "javascript:alert(1)",
            "data:text/html,<script>",
            "not-a-url",
        ],
    )
    def test_non_http_schemes_rejected(self, runner: CliRunner, url: str) -> None:
        result = runner.invoke(app, ["scrape", url, "--dataset-id", "d"])
        assert result.exit_code == int(ExitCode.INVALID_INPUT)


class TestIdentifierValidation:
    @pytest.mark.parametrize("dataset_id", ["../evil", "a b", "drop;table", "a/b"])
    def test_non_alphanumeric_dataset_id_rejected(self, runner: CliRunner, dataset_id: str) -> None:
        result = runner.invoke(
            app,
            ["scrape", "https://mock.local/", "--dataset-id", dataset_id, "--from-file", "x"],
        )
        assert result.exit_code == int(ExitCode.INVALID_INPUT)
