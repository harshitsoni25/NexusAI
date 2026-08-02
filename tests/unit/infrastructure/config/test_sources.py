"""Individual configuration sources."""

from __future__ import annotations

from pathlib import Path

import pytest

from nexusai.domain.errors import ConfigurationError
from nexusai.infrastructure.config.sources import (
    CliOverrideSource,
    DefaultsSource,
    EnvironmentSource,
    YamlFileSource,
)


def test_defaults_source_returns_its_values() -> None:
    source = DefaultsSource({"logging": {"level": "INFO"}})
    assert source.load() == {"logging": {"level": "INFO"}}
    assert "default" in source.name


def test_yaml_file_is_parsed(config_dir: Path) -> None:
    path = config_dir / "app.yaml"
    path.write_text("logging:\n  level: DEBUG\n", encoding="utf-8")
    assert YamlFileSource(path).load() == {"logging": {"level": "DEBUG"}}


def test_an_empty_yaml_file_is_an_empty_layer(config_dir: Path) -> None:
    path = config_dir / "empty.yaml"
    path.write_text("", encoding="utf-8")
    assert YamlFileSource(path).load() == {}


def test_a_missing_required_file_is_an_error(config_dir: Path) -> None:
    with pytest.raises(ConfigurationError, match="not found"):
        YamlFileSource(config_dir / "absent.yaml").load()


def test_a_missing_optional_file_is_an_empty_layer(config_dir: Path) -> None:
    # This is what lets a default location be probed without forcing every
    # deployment to create one.
    assert YamlFileSource(config_dir / "absent.yaml", required=False).load() == {}


def test_malformed_yaml_is_reported_with_its_path(config_dir: Path) -> None:
    path = config_dir / "broken.yaml"
    path.write_text("logging: [unclosed\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="not valid YAML") as caught:
        YamlFileSource(path).load()
    assert caught.value.context["path"] == str(path)


def test_a_yaml_file_must_hold_a_mapping(config_dir: Path) -> None:
    path = config_dir / "list.yaml"
    path.write_text("- one\n- two\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="mapping at the top level"):
        YamlFileSource(path).load()


def test_environment_variables_become_nested_keys() -> None:
    source = EnvironmentSource({"NEXUSAI_LOGGING__CONSOLE__LEVEL": "DEBUG"})
    assert source.load() == {"logging": {"console": {"level": "DEBUG"}}}


def test_unprefixed_variables_are_ignored() -> None:
    assert EnvironmentSource({"PATH": "/usr/bin", "HOME": "/root"}).load() == {}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("true", True),
        ("false", False),
        ("42", 42),
        ("1.5", 1.5),
        ("null", None),
        ("plain", "plain"),
    ],
)
def test_environment_values_are_typed_not_stringly(raw: str, expected: object) -> None:
    # Without this, `NEXUSAI_LOGGING__CONSOLE__ENABLED=false` would arrive as
    # the string "false", which is truthy, and quietly do the opposite.
    loaded = EnvironmentSource({"NEXUSAI_KEY": raw}).load()
    assert loaded["key"] == expected


def test_empty_key_segments_are_rejected() -> None:
    with pytest.raises(ConfigurationError, match="empty key segment"):
        EnvironmentSource({"NEXUSAI_LOGGING____LEVEL": "DEBUG"}).load()


def test_cli_overrides_use_dotted_paths() -> None:
    assert CliOverrideSource(["logging.level=DEBUG"]).load() == {"logging": {"level": "DEBUG"}}


@pytest.mark.parametrize("override", ["logging.level", "=DEBUG", "logging..level=DEBUG"])
def test_malformed_overrides_are_rejected(override: str) -> None:
    with pytest.raises(ConfigurationError):
        CliOverrideSource([override]).load()


def test_an_override_cannot_burrow_into_a_scalar() -> None:
    with pytest.raises(ConfigurationError, match="not a mapping"):
        CliOverrideSource(["logging=INFO", "logging.level=DEBUG"]).load()


def test_multiple_overrides_merge_into_one_layer() -> None:
    loaded = CliOverrideSource(["logging.level=DEBUG", "logging.console.colorize=false"]).load()
    assert loaded == {"logging": {"level": "DEBUG", "console": {"colorize": False}}}


def test_an_unreadable_file_is_reported_as_a_configuration_error(config_dir: Path) -> None:
    # A directory where a file was expected is the common shape of this mistake.
    directory = config_dir / "as_a_directory.yaml"
    directory.mkdir()
    with pytest.raises(ConfigurationError, match="could not be read"):
        YamlFileSource(directory).load()


def test_a_value_that_is_not_valid_yaml_stays_a_plain_string() -> None:
    # Scraped and user-supplied values are not YAML documents. A stray bracket
    # must not turn into a parse failure at startup.
    loaded = EnvironmentSource({"NEXUSAI_KEY": "[unclosed"}).load()
    assert loaded["key"] == "[unclosed"


def test_a_structured_value_is_parsed_into_a_list() -> None:
    loaded = EnvironmentSource({"NEXUSAI_PLUGINS__ALLOWLIST": '["a:B", "c:D"]'}).load()
    assert loaded["plugins"] == {"allowlist": ["a:B", "c:D"]}
