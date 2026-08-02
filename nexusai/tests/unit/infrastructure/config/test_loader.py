"""The precedence chain, end to end."""

from __future__ import annotations

from pathlib import Path

import pytest

from nexusai.domain.errors import ConfigurationError
from nexusai.infrastructure.config.loader import ConfigurationLoader
from nexusai.infrastructure.config.settings import Environment, LogLevel


def test_defaults_apply_when_nothing_is_configured(
    loader: ConfigurationLoader, tmp_path: Path
) -> None:
    loaded = loader.load(environ={}, dotenv_path=tmp_path / "none.env")
    assert loaded.settings.environment is Environment.LOCAL
    assert loaded.settings.logging.level is LogLevel.INFO


def test_yaml_overrides_defaults(
    loader: ConfigurationLoader, config_dir: Path, tmp_path: Path
) -> None:
    path = config_dir / "app.yaml"
    path.write_text("logging:\n  level: WARNING\n", encoding="utf-8")
    loaded = loader.load(config_file=path, environ={}, dotenv_path=tmp_path / "none.env")
    assert loaded.settings.logging.level is LogLevel.WARNING


def test_environment_overrides_yaml(
    loader: ConfigurationLoader, config_dir: Path, tmp_path: Path
) -> None:
    path = config_dir / "app.yaml"
    path.write_text("logging:\n  level: WARNING\n", encoding="utf-8")
    loaded = loader.load(
        config_file=path,
        environ={"NEXUSAI_LOGGING__LEVEL": "ERROR"},
        dotenv_path=tmp_path / "none.env",
    )
    assert loaded.settings.logging.level is LogLevel.ERROR


def test_cli_overrides_everything(
    loader: ConfigurationLoader, config_dir: Path, tmp_path: Path
) -> None:
    path = config_dir / "app.yaml"
    path.write_text("logging:\n  level: WARNING\n", encoding="utf-8")
    loaded = loader.load(
        config_file=path,
        overrides=("logging.level=DEBUG",),
        environ={"NEXUSAI_LOGGING__LEVEL": "ERROR"},
        dotenv_path=tmp_path / "none.env",
    )
    assert loaded.settings.logging.level is LogLevel.DEBUG


def test_real_environment_wins_over_the_dotenv_file(
    loader: ConfigurationLoader, tmp_path: Path
) -> None:
    # .env is a developer convenience. It must never override a deployment.
    dotenv = tmp_path / ".env"
    dotenv.write_text("NEXUSAI_LOGGING__LEVEL=DEBUG\n", encoding="utf-8")
    loaded = loader.load(environ={"NEXUSAI_LOGGING__LEVEL": "ERROR"}, dotenv_path=dotenv)
    assert loaded.settings.logging.level is LogLevel.ERROR


def test_the_dotenv_file_applies_when_the_environment_is_silent(
    loader: ConfigurationLoader, tmp_path: Path
) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("NEXUSAI_LOGGING__LEVEL=DEBUG\n", encoding="utf-8")
    loaded = loader.load(environ={}, dotenv_path=dotenv)
    assert loaded.settings.logging.level is LogLevel.DEBUG


def test_an_invalid_value_names_the_key_the_value_and_the_source(
    loader: ConfigurationLoader, tmp_path: Path
) -> None:
    with pytest.raises(ConfigurationError) as caught:
        loader.load(
            overrides=("logging.level=VERBOSE",), environ={}, dotenv_path=tmp_path / "n.env"
        )
    message = str(caught.value)
    assert "logging.level" in message
    assert "VERBOSE" in message
    assert "command line override" in message


def test_an_unknown_key_is_rejected_rather_than_ignored(
    loader: ConfigurationLoader, tmp_path: Path
) -> None:
    # A silently ignored typo leaves an operator wondering why their change had
    # no effect. Failing loudly is the whole reason for extra="forbid".
    with pytest.raises(ConfigurationError, match="loging"):
        loader.load(overrides=("loging.level=DEBUG",), environ={}, dotenv_path=tmp_path / "n.env")


def test_every_invalid_key_is_reported_not_just_the_first(
    loader: ConfigurationLoader, tmp_path: Path
) -> None:
    with pytest.raises(ConfigurationError) as caught:
        loader.load(
            overrides=("logging.level=VERBOSE", "environment=orbit"),
            environ={},
            dotenv_path=tmp_path / "n.env",
        )
    assert caught.value.context["invalid_keys"] == ("environment", "logging.level")


def test_a_missing_explicit_config_file_is_fatal(
    loader: ConfigurationLoader, tmp_path: Path
) -> None:
    with pytest.raises(ConfigurationError, match="not found"):
        loader.load(
            config_file=tmp_path / "absent.yaml", environ={}, dotenv_path=tmp_path / "n.env"
        )


def test_the_source_trail_is_retained_for_auditing(
    loader: ConfigurationLoader, tmp_path: Path
) -> None:
    loaded = loader.load(
        overrides=("logging.level=DEBUG",), environ={}, dotenv_path=tmp_path / "n.env"
    )
    assert "built-in defaults" in loaded.source_names[0]
    assert "command line override" in loaded.source_names[-1]


def test_settings_are_frozen(loader: ConfigurationLoader, tmp_path: Path) -> None:
    loaded = loader.load(environ={}, dotenv_path=tmp_path / "n.env")
    with pytest.raises(ValueError, match="frozen"):
        loaded.settings.logging.level = LogLevel.DEBUG


def test_the_packaged_defaults_file_is_optional(tmp_path: Path) -> None:
    loader = ConfigurationLoader(packaged_defaults=tmp_path / "absent.yaml")
    assert loader.load(environ={}, dotenv_path=tmp_path / "n.env").settings is not None
