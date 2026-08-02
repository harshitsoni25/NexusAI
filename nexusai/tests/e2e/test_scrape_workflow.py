"""End-to-end: complete workflows through the public CLI entry points.

These drive the framework the way a user does — through ``nexusai`` commands —
against controlled offline fixtures, never the network. They verify that a scrape
runs to a terminal state, that its dataset is queryable, and that analysis,
statistics and doctor behave as documented, exercising presentation, application,
domain and infrastructure together.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nexusai.presentation.cli.app import app
from mock_sites import product_listing, static_page

pytestmark = pytest.mark.e2e


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def isolated_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXUSAI_PATHS__ROOT", str(tmp_path / "hk"))


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _clean(output: str) -> str:
    return _ANSI.sub("", output)


def _json(output: str) -> dict[str, object]:
    text = _clean(output)
    result: dict[str, object] = json.loads(text[text.index("{") :])
    return result


def _array(output: str) -> list[object]:
    text = _clean(output)
    match = re.search(r"\[\s*(?:\{|\])[\s\S]*\]", text)
    assert match is not None
    listed: list[object] = json.loads(match.group(0))
    return listed


class TestScrapeToState:
    def test_offline_scrape_completes(self, runner: CliRunner, tmp_path: Path) -> None:
        page = tmp_path / "page.html"
        page.write_bytes(static_page(title="Catalogue"))
        result = runner.invoke(
            app,
            [
                "scrape",
                "https://mock.local/",
                "--dataset-id",
                "cat",
                "--from-file",
                str(page),
                "--json",
            ],
        )
        assert result.exit_code == 0
        data = _json(result.output)
        assert data["state"] == "completed"
        assert data["dataset_ref"] == "cat"

    def test_scrape_then_jobs_and_stats(self, runner: CliRunner, tmp_path: Path) -> None:
        page = tmp_path / "p.html"
        page.write_bytes(product_listing(5))
        runner.invoke(
            app,
            [
                "scrape",
                "https://mock.local/",
                "--dataset-id",
                "prod",
                "--from-file",
                str(page),
                "--json",
            ],
        )
        jobs = runner.invoke(app, ["jobs", "--json"])
        assert jobs.exit_code == 0
        listed = _array(jobs.output)
        assert len(listed) >= 1
        stats = runner.invoke(app, ["stats", "--json"])
        assert stats.exit_code == 0
        assert "jobs" in _json(stats.output)


class TestAnalysisWorkflow:
    def test_analyze_recommends_a_strategy(self, runner: CliRunner, tmp_path: Path) -> None:
        page = tmp_path / "a.html"
        page.write_bytes(product_listing(8))
        result = runner.invoke(
            app, ["analyze-site", "https://mock.local/", "--from-file", str(page), "--json"]
        )
        assert result.exit_code == 0
        assert "recommendation" in _json(result.output)


class TestDoctorAndVersion:
    def test_doctor_runs(self, runner: CliRunner) -> None:
        assert runner.invoke(app, ["doctor", "--json"]).exit_code in {0, 9}

    def test_version(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "nexusai" in result.output.lower() or "0.1.0" in result.output
