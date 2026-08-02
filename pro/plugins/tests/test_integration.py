"""Integration test: a real plugin distribution is installed, discovered by the
engine (reused), surfaced by the manager, and removed.

This proves the manager reads the engine's *actual* discovery — not a mock — for
details/version/list, and that install/remove drive real pip. It is marked
``integration`` so it can be deselected where pip installs are undesirable.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from nexusai_pro_plugins import RuntimeState, build_manager

DIST_NAME = "hk-fixture-plugin"
PLUGIN_ID = "fixture-exporter"


def _write_fixture(root: Path) -> Path:
    pkg = root / "hk_fixture_plugin"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text(
        textwrap.dedent(
            '''
            """A minimal valid Nexus AI plugin used as a test fixture."""
            from nexusai.domain.model.plugin import ApiVersion, ExtensionPoint, PluginMetadata


            class FixtureExporter:
                @property
                def metadata(self) -> PluginMetadata:
                    return PluginMetadata(
                        name="fixture-exporter",
                        version="0.3.1",
                        extension_point=ExtensionPoint.EXPORTER,
                        api_version=ApiVersion(1, 0),
                        description="A fixture exporter plugin",
                        author="tests",
                    )

                def initialize(self) -> None:  # noqa: D401
                    pass

                def dispose(self) -> None:  # noqa: D401
                    pass


            def build() -> FixtureExporter:
                return FixtureExporter()
            '''
        ),
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        textwrap.dedent(
            f'''
            [build-system]
            requires = ["hatchling"]
            build-backend = "hatchling.build"

            [project]
            name = "{DIST_NAME}"
            version = "0.3.1"
            description = "Nexus AI fixture plugin"
            requires-python = ">=3.12"

            [project.entry-points."nexusai.plugins"]
            fixture-exporter = "hk_fixture_plugin:build"

            [tool.hatch.build.targets.wheel]
            packages = ["hk_fixture_plugin"]
            '''
        ),
        encoding="utf-8",
    )
    return root


def _pip(*args: str) -> int:
    return subprocess.run([sys.executable, "-m", "pip", *args], capture_output=True, text=True).returncode


@pytest.mark.integration
def test_install_discover_manage_remove(tmp_path):
    project = _write_fixture(tmp_path / "fixture")
    manager = build_manager()

    # Install the fixture plugin distribution via the manager.
    result = manager.install(str(project))
    assert result.ok, result.stderr
    try:
        # Reuse the engine's real discovery: the plugin should be LOADED.
        view = manager.details(PLUGIN_ID)
        assert view is not None, "manager did not surface the installed plugin"
        assert view.state is RuntimeState.LOADED
        assert view.runtime and view.runtime.version == "0.3.1"
        assert view.runtime.extension_point == "exporter"
        assert view.distribution and view.distribution_version == "0.3.1"

        # Enable/disable is a Pro overlay that does not uninstall.
        assert PLUGIN_ID in manager.effective_plugin_names()
        manager.disable(PLUGIN_ID)
        assert PLUGIN_ID not in manager.effective_plugin_names()
        assert manager.details(PLUGIN_ID).state is RuntimeState.LOADED  # still installed
        manager.enable(PLUGIN_ID)
        assert PLUGIN_ID in manager.effective_plugin_names()
    finally:
        removed = manager.remove(PLUGIN_ID)
        assert removed.ok, removed.stderr

    # After removal the plugin is gone from discovery.
    assert manager.details(PLUGIN_ID) is None
    _pip("uninstall", "-y", DIST_NAME)  # belt-and-braces cleanup
