"""Tests for the Phase 7 CLI commands: invocation, validation, exit codes, JSON."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from nexusai.presentation.cli.app import app
from nexusai.presentation.cli.exit_codes import ExitCode

_HTML = "<html><head><title>T</title></head><body><h1>H</h1><p>text</p></body></html>"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def isolated_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXUSAI_PATHS__ROOT", str(tmp_path / "hk"))


@pytest.fixture
def html_file(tmp_path: Path) -> Path:
    path = tmp_path / "page.html"
    path.write_text(_HTML)
    return path


class TestDoctor:
    def test_json_reports_ok(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["doctor", "--json"])
        assert result.exit_code == 0
        assert json.loads(_json_of(result.output))["ok"] is True


class TestAnalyzeSite:
    def test_from_file_json_has_recommendation(self, runner: CliRunner, html_file: Path) -> None:
        result = runner.invoke(
            app, ["analyze-site", "https://x/", "--from-file", str(html_file), "--json"]
        )
        assert result.exit_code == 0
        assert "recommendation" in result.output

    def test_bad_scheme_is_rejected(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["analyze-site", "ftp://x/"])
        assert result.exit_code == int(ExitCode.INVALID_INPUT)


class TestScrape:
    def test_offline_run_completes(self, runner: CliRunner, html_file: Path) -> None:
        result = runner.invoke(
            app,
            [
                "scrape",
                "https://s.example.com/",
                "--dataset-id",
                "cat",
                "--from-file",
                str(html_file),
                "--json",
            ],
        )
        assert result.exit_code == int(ExitCode.SUCCESS)
        assert json.loads(_json_of(result.output))["state"] == "completed"

    def test_bad_dataset_id_rejected(self, runner: CliRunner, html_file: Path) -> None:
        result = runner.invoke(
            app, ["scrape", "https://x/", "--dataset-id", "bad id!", "--from-file", str(html_file)]
        )
        assert result.exit_code == int(ExitCode.INVALID_INPUT)


class TestJobsAndStats:
    def test_jobs_json(self, runner: CliRunner) -> None:
        assert runner.invoke(app, ["jobs", "--json"]).exit_code == 0

    def test_jobs_bad_limit_rejected(self, runner: CliRunner) -> None:
        assert runner.invoke(app, ["jobs", "--limit", "0"]).exit_code == int(ExitCode.INVALID_INPUT)

    def test_stats_json(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["stats", "--json"])
        assert result.exit_code == 0
        assert "total_jobs" in result.output


class TestSchedule:
    def test_create_then_list(self, runner: CliRunner) -> None:
        create = runner.invoke(
            app,
            [
                "schedule",
                "create",
                "--name",
                "daily",
                "--target",
                "https://x/",
                "--interval-seconds",
                "3600",
            ],
        )
        assert create.exit_code == 0
        listed = runner.invoke(app, ["schedule", "list", "--json"])
        assert "daily" in listed.output

    def test_bad_target_rejected(self, runner: CliRunner) -> None:
        result = runner.invoke(
            app,
            [
                "schedule",
                "create",
                "--name",
                "x",
                "--target",
                "notaurl",
                "--interval-seconds",
                "60",
            ],
        )
        assert result.exit_code == int(ExitCode.INVALID_INPUT)


class TestValidateExportReport:
    def test_validate_from_file(self, runner: CliRunner, html_file: Path) -> None:
        result = runner.invoke(app, ["validate", "shop", "--from-file", str(html_file), "--json"])
        assert result.exit_code == 0
        assert "records" in result.output

    def test_export_from_file(self, runner: CliRunner, html_file: Path) -> None:
        result = runner.invoke(
            app, ["export", "shop", "--from-file", str(html_file), "--format", "csv"]
        )
        assert result.exit_code == 0

    def test_report_from_file(self, runner: CliRunner, html_file: Path) -> None:
        result = runner.invoke(
            app, ["report", "shop", "--from-file", str(html_file), "--format", "html"]
        )
        assert result.exit_code == 0


class TestBenchmark:
    def test_benchmark_json(self, runner: CliRunner) -> None:
        result = runner.invoke(
            app, ["benchmark", "--scenario", "extraction", "--iterations", "2", "--json"]
        )
        assert result.exit_code == 0
        assert "median_seconds" in result.output

    def test_bad_iterations_rejected(self, runner: CliRunner) -> None:
        assert runner.invoke(app, ["benchmark", "--iterations", "0"]).exit_code == int(
            ExitCode.INVALID_INPUT
        )


def _json_of(output: str) -> str:
    start = output.index("{")
    return output[start:]


class TestHumanReadableRendering:
    """Exercise the Rich (non-JSON) render branches of each command."""

    def test_doctor_table(self, runner: CliRunner) -> None:
        assert runner.invoke(app, ["doctor"]).exit_code == 0

    def test_jobs_table(self, runner: CliRunner) -> None:
        assert runner.invoke(app, ["jobs"]).exit_code == 0

    def test_stats_table(self, runner: CliRunner) -> None:
        assert runner.invoke(app, ["stats"]).exit_code == 0

    def test_analyze_table(self, runner: CliRunner, html_file: Path) -> None:
        result = runner.invoke(app, ["analyze-site", "https://x/", "--from-file", str(html_file)])
        assert result.exit_code == 0
        assert "Recommended strategy" in result.output

    def test_scrape_table_then_status(self, runner: CliRunner, html_file: Path) -> None:
        scrape = runner.invoke(
            app,
            [
                "scrape",
                "https://s.example.com/",
                "--dataset-id",
                "cat",
                "--from-file",
                str(html_file),
            ],
        )
        assert scrape.exit_code == 0
        job_id = scrape.output.split("Job ")[1].split(" ")[0].strip()
        status = runner.invoke(app, ["status", job_id])
        assert status.exit_code == 0
        status_json = runner.invoke(app, ["status", job_id, "--json"])
        assert json.loads(_json_of(status_json.output))["state"] == "completed"

    def test_schedule_enable_disable_delete(self, runner: CliRunner) -> None:
        create = runner.invoke(
            app,
            [
                "schedule",
                "create",
                "--name",
                "s",
                "--target",
                "https://x/",
                "--interval-seconds",
                "60",
            ],
        )
        marker = "Created schedule "
        line = next(ln for ln in create.output.splitlines() if marker in ln)
        schedule_id = line.split(marker)[1].split(" ")[0].strip()
        assert runner.invoke(app, ["schedule", "disable", schedule_id]).exit_code == 0
        assert runner.invoke(app, ["schedule", "enable", schedule_id]).exit_code == 0
        assert runner.invoke(app, ["schedule", "delete", schedule_id]).exit_code == 0

    def test_analyze_bad_strategy_rejected(self, runner: CliRunner, html_file: Path) -> None:
        result = runner.invoke(
            app,
            [
                "analyze-site",
                "https://x/",
                "--from-file",
                str(html_file),
                "--strategy",
                "telepathy",
            ],
        )
        assert result.exit_code == int(ExitCode.INVALID_INPUT)

    def test_schedule_bad_overlap_rejected(self, runner: CliRunner) -> None:
        result = runner.invoke(
            app,
            [
                "schedule",
                "create",
                "--name",
                "s",
                "--target",
                "https://x/",
                "--interval-seconds",
                "60",
                "--overlap",
                "sometimes",
            ],
        )
        assert result.exit_code == int(ExitCode.INVALID_INPUT)


class TestResumeCommand:
    def test_resume_unknown_job_fails_cleanly(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["resume", "no-such-job"])
        assert result.exit_code != 0
