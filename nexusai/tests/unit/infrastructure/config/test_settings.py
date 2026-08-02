"""The settings schema."""

from __future__ import annotations

from pathlib import Path

import pytest

from nexusai.infrastructure.config.settings import FrameworkSettings, PathSettings


def test_relative_paths_resolve_beneath_the_root(tmp_path: Path) -> None:
    root = tmp_path / "srv" / "nexusai"
    paths = PathSettings(root=root, data=Path("data"))
    assert paths.resolve("data") == root / "data"


def test_absolute_paths_are_respected(tmp_path: Path) -> None:
    # A deployment that mounts one directory elsewhere should not have it
    # silently relocated under the root. ``tmp_path`` gives a platform-correct
    # absolute path so the assertion holds on POSIX and Windows alike.
    elsewhere = tmp_path / "mnt" / "blobs"
    paths = PathSettings(root=tmp_path / "srv" / "nexusai", artifacts=elsewhere)
    assert paths.resolve("artifacts") == elsewhere


def test_an_unknown_directory_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown path"):
        PathSettings().resolve("nowhere")


@pytest.mark.parametrize("name", ["data", "artifacts", "reports", "logs", "state"])
def test_every_configured_directory_resolves(name: str) -> None:
    assert PathSettings().resolve(name).is_absolute()


def test_unknown_keys_are_rejected() -> None:
    with pytest.raises(ValueError, match="Extra inputs"):
        FrameworkSettings.model_validate({"scraping": {"concurrency": 8}})


def test_the_default_configuration_is_valid() -> None:
    settings = FrameworkSettings()
    assert settings.plugins.discovery_enabled is True
    assert settings.logging.file.enabled is False


def test_traceback_variable_capture_is_off_by_default() -> None:
    # Those values can contain secrets and this output frequently ends up in
    # shared log aggregation.
    assert FrameworkSettings().logging.diagnose is False
