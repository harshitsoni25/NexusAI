"""The command line interface, exercised through its public entry point."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from nexusai.__about__ import __version__
from nexusai.domain.model.plugin import ApiVersion
from nexusai.presentation.cli.app import app
from nexusai.presentation.cli.commands.diagnose import _writability
from nexusai.presentation.cli.exit_codes import ExitCode
from nexusai.presentation.cli.rendering.console import exit_code_for
from nexusai.presentation.cli.state import CliState, resolve_overrides
from nexusai.testing import StubPlugin

runner = CliRunner()


@pytest.fixture
def workspace(tmp_path: Path) -> list[str]:
    """Global options that keep a command's output inside a temporary directory."""
    return ["--set", f"paths.root={tmp_path}"]


def test_help_is_shown_when_no_command_is_given() -> None:
    result = runner.invoke(app, [])
    assert "Usage" in result.output


def test_the_version_flag_short_circuits_startup() -> None:
    # Printing a version must not read configuration files or discover plugins.
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_the_version_command_reports_the_version() -> None:
    result = runner.invoke(app, ["version"])
    assert __version__ in result.output


def test_verbose_version_includes_the_interpreter() -> None:
    result = runner.invoke(app, ["version", "--verbose"])
    assert "Python" in result.output


def test_config_show_lists_settings_and_their_origins(workspace: list[str]) -> None:
    result = runner.invoke(app, [*workspace, "config", "show"])
    assert result.exit_code == 0
    assert "logging.level" in result.output


def test_config_show_can_emit_json(workspace: list[str]) -> None:
    result = runner.invoke(app, [*workspace, "config", "show", "--json"])
    assert result.exit_code == 0
    assert "settings" in result.output


def test_config_validate_accepts_a_valid_configuration(workspace: list[str]) -> None:
    result = runner.invoke(app, [*workspace, "config", "validate"])
    assert result.exit_code == 0
    assert "valid" in result.output


def test_an_invalid_override_exits_with_the_configuration_code() -> None:
    # Schedulers and CI act on exit codes, so the distinction between "you typed
    # something wrong" and "the run went badly" has to survive to the shell.
    result = runner.invoke(app, ["--set", "logging.level=NONSENSE", "config", "validate"])
    assert result.exit_code == ExitCode.CONFIGURATION_ERROR


def test_an_unknown_setting_is_rejected_rather_than_ignored() -> None:
    result = runner.invoke(app, ["--set", "nonsense.key=1", "config", "validate"])
    assert result.exit_code == ExitCode.CONFIGURATION_ERROR


def test_a_missing_config_file_is_reported() -> None:
    result = runner.invoke(app, ["--config", "/nonexistent/config.yaml", "config", "validate"])
    assert result.exit_code == ExitCode.CONFIGURATION_ERROR


def test_plugins_list_reports_an_empty_ecosystem(workspace: list[str]) -> None:
    result = runner.invoke(
        app, [*workspace, "--set", "plugins.discovery_enabled=false", "plugins", "list"]
    )
    assert result.exit_code == 0
    assert "No plugins" in result.output


def test_plugins_contracts_lists_every_extension_point() -> None:
    result = runner.invoke(app, ["plugins", "contracts"])
    assert result.exit_code == 0
    assert "site_adapter" in result.output


def test_diagnose_reports_the_startup_path(workspace: list[str]) -> None:
    result = runner.invoke(app, [*workspace, "diagnose"])
    assert result.exit_code == 0
    assert "Correlation id" in result.output


def test_diagnose_verifies_that_configured_directories_are_writable(
    workspace: list[str], tmp_path: Path
) -> None:
    runner.invoke(app, [*workspace, "diagnose"])
    assert (tmp_path / "data").exists()


def test_verbosity_flags_travel_through_the_normal_precedence_chain() -> None:
    assert resolve_overrides(None, verbose=True, quiet=False) == (
        "logging.level=DEBUG",
        "logging.console.level=DEBUG",
    )
    assert resolve_overrides("warning", verbose=False, quiet=False) == (
        "logging.level=WARNING",
        "logging.console.level=WARNING",
    )
    assert resolve_overrides(None, verbose=False, quiet=False) == ()


def test_quiet_and_verbose_together_is_rejected() -> None:
    result = runner.invoke(app, ["--quiet", "--verbose", "version"])
    assert result.exit_code != 0


def test_the_container_is_built_only_once_per_invocation(tmp_path: Path) -> None:
    state = CliState(overrides=(f"paths.root={tmp_path}",))
    # Read into locals: MyPy narrows a property access and would otherwise treat
    # the second assertion as impossible.
    built_before = state.is_built
    first = state.container()
    built_after = state.is_built
    assert (built_before, built_after) == (False, True)
    assert state.container() is first


def test_exit_codes_distinguish_failure_kinds() -> None:
    from nexusai.domain.errors import ConfigurationError, InternalError, StorageError

    assert exit_code_for(ConfigurationError("x")) is ExitCode.CONFIGURATION_ERROR
    assert exit_code_for(InternalError("x")) is ExitCode.INTERNAL_ERROR
    assert exit_code_for(StorageError("x")) is ExitCode.FAILURE


# --------------------------------------------------------------------------- #
# Plugin listing needs a plugin to list. The test module is already imported, so
# it can act as its own plugin distribution without a fixture file on disk.
# --------------------------------------------------------------------------- #


def SamplePlugin() -> StubPlugin:  # noqa: N802 - referenced as a factory by name
    return StubPlugin(name="sample")


def FuturePlugin() -> StubPlugin:  # noqa: N802
    return StubPlugin(name="future", api_version=ApiVersion(9, 0))


def test_plugins_list_shows_a_registered_plugin(workspace: list[str]) -> None:
    result = runner.invoke(
        app,
        [*workspace, "--set", f'plugins.allowlist=["{__name__}:SamplePlugin"]', "plugins", "list"],
    )
    assert result.exit_code == 0
    assert "sample" in result.output


def test_plugins_list_shows_rejections_with_their_reason(workspace: list[str]) -> None:
    # A plugin that silently failed to load looks identical to one never
    # installed, so rejections appear beside acceptances rather than in a log.
    result = runner.invoke(
        app,
        [*workspace, "--set", f'plugins.allowlist=["{__name__}:FuturePlugin"]', "plugins", "list"],
    )
    assert result.exit_code == 0
    assert "Rejected" in result.output


def test_diagnose_reports_a_directory_it_cannot_create(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    assert "not writable" in _writability(blocker / "data")
