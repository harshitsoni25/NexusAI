"""Regression guard for Docker packaging (Phase 10R-CV R4).

A C2 build failed because the Dockerfile's build stage did not stage ``LICENSE``,
which ``pyproject.toml`` references via ``license = { file = "LICENSE" }`` and which
hatchling reads while building the wheel. This test protects that defect *class*: it
derives the files the build metadata requires (the readme and the license file) from
``pyproject.toml`` and asserts each is both present at the repository root and copied
into the Docker build stage. It is deterministic and needs no Docker daemon.

It is intentionally narrow -- it reads the two metadata file references and checks the
build-stage ``COPY`` lines; it is not a general Dockerfile parser.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]


def _required_build_files() -> set[str]:
    """Files the wheel build reads, derived from pyproject metadata.

    Covers the readme and a file-based license reference -- the inputs hatchling
    validates during ``python -m build --wheel``.
    """
    data = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    required: set[str] = set()

    readme = project.get("readme")
    if isinstance(readme, str):
        required.add(readme)
    elif isinstance(readme, dict) and isinstance(readme.get("file"), str):
        required.add(readme["file"])

    license_field = project.get("license")
    if isinstance(license_field, dict) and isinstance(license_field.get("file"), str):
        required.add(license_field["file"])

    return required


def _build_stage_copy_sources() -> set[str]:
    """The local paths copied into the Docker build stage.

    Only ``COPY`` lines that bring files in from the build context are considered;
    ``COPY --from=`` (inter-stage copies) are ignored. Each line's final token is the
    destination, so the remaining tokens are the sources.
    """
    sources: set[str] = set()
    for raw in (_ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.upper().startswith("COPY ") or "--from=" in line:
            continue
        tokens = line.split()[1:]  # drop the COPY keyword
        sources.update(tokens[:-1])  # drop the destination token
    return sources


class TestDockerBuildStageStagesMetadataFiles:
    def test_required_files_exist_at_repository_root(self) -> None:
        for name in _required_build_files():
            assert (_ROOT / name).exists(), f"metadata references missing file: {name}"

    def test_required_files_are_copied_into_the_build_stage(self) -> None:
        required = _required_build_files()
        staged = _build_stage_copy_sources()
        missing = required - staged
        assert not missing, (
            f"Dockerfile build stage does not COPY metadata-required file(s): {missing}. "
            f"Staged sources: {staged}"
        )

    def test_guard_covers_readme_and_license_explicitly(self) -> None:
        # The two references the C2 failure hinged on must be in scope.
        required = _required_build_files()
        assert "README.md" in required
        assert "LICENSE" in required
