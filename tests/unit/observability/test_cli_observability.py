"""Tests for the Phase 8 CLI: benchmark, stats catalog/health, doctor health."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from nexusai.presentation.cli.app import app
from nexusai.presentation.cli.exit_codes import ExitCode


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def isolated_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXUSAI_PATHS__ROOT", str(tmp_path / "hk"))


def _obj(output: str) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(output[output.index("{") :])
    return result


class TestBenchmarkCommand:
    def test_runs_scenario_json(self, runner: CliRunner) -> None:
        result = runner.invoke(
            app,
            [
                "benchmark",
                "--scenario",
                "extraction",
                "--size",
                "small",
                "--iterations",
                "3",
                "--json",
            ],
        )
        assert result.exit_code == 0
        data = _obj(result.output)
        assert data["scenarios"][0]["scenario"] == "extraction"
        assert data["scenarios"][0]["errors"] == 0

    def test_record_and_compare_baseline(self, runner: CliRunner) -> None:
        record = runner.invoke(
            app,
            [
                "benchmark",
                "--scenario",
                "processing",
                "--size",
                "small",
                "--iterations",
                "3",
                "--record-baseline",
                "--json",
            ],
        )
        assert _obj(record.output)["scenarios"][0]["baseline_recorded"] is True
        compare = runner.invoke(
            app,
            [
                "benchmark",
                "--scenario",
                "processing",
                "--size",
                "small",
                "--iterations",
                "3",
                "--compare",
                "--json",
            ],
        )
        verdict = _obj(compare.output)["scenarios"][0]["comparison"]["verdict"]
        assert verdict in {"improvement", "stable", "regression", "inconclusive"}

    def test_compare_without_baseline_is_inconclusive(self, runner: CliRunner) -> None:
        result = runner.invoke(
            app,
            [
                "benchmark",
                "--scenario",
                "export",
                "--size",
                "small",
                "--iterations",
                "2",
                "--compare",
                "--json",
            ],
        )
        assert _obj(result.output)["scenarios"][0]["comparison"]["verdict"] == "inconclusive"

    def test_table_notes_not_verified(self, runner: CliRunner) -> None:
        result = runner.invoke(
            app, ["benchmark", "--scenario", "extraction", "--size", "small", "--iterations", "2"]
        )
        assert result.exit_code == 0
        assert "NOT VERIFIED" in result.output

    def test_bad_size_rejected(self, runner: CliRunner) -> None:
        assert runner.invoke(app, ["benchmark", "--size", "huge"]).exit_code == int(
            ExitCode.INVALID_INPUT
        )

    def test_bad_iterations_rejected(self, runner: CliRunner) -> None:
        assert runner.invoke(app, ["benchmark", "--iterations", "0"]).exit_code == int(
            ExitCode.INVALID_INPUT
        )

    def test_unknown_scenario_rejected(self, runner: CliRunner) -> None:
        assert runner.invoke(app, ["benchmark", "--scenario", "ghost"]).exit_code == int(
            ExitCode.INVALID_INPUT
        )


class TestStatsObservability:
    def test_catalog_json_lists_metrics(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["stats", "--catalog", "--json"])
        assert result.exit_code == 0
        assert len(_obj(result.output)["metrics"]) > 30

    def test_catalog_table(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["stats", "--catalog"])
        assert result.exit_code == 0
        assert "nexusai.job.finished" in result.output

    def test_stats_includes_health(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["stats", "--json"])
        assert result.exit_code == 0
        assert "health" in _obj(result.output)

    def test_stats_table(self, runner: CliRunner) -> None:
        assert runner.invoke(app, ["stats"]).exit_code == 0


class TestDoctorHealth:
    def test_doctor_json_includes_operational_health(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["doctor", "--json"])
        assert result.exit_code == 0
        assert "operational_health" in _obj(result.output)

    def test_doctor_table_shows_health(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Operational health" in result.output
