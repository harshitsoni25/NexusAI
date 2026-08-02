"""Regression guard for the optional-dependency / CI type-check contract (R6).

MyPy (run in the CI ``quality`` job) type-checks all of ``src``, including modules
that lazily import optional-extra dependencies. For MyPy to resolve such an import
without error, the dependency must either be installed in the quality job or be
covered by ``ignore_missing_imports`` in the MyPy config. ``Pillow``/``PIL`` was
neither -- it was omitted from the overrides and not installed -- so CI's MyPy failed
on ``from PIL import ...`` while every other optional extra passed.

This guard encodes the contract: for each optional-feature extra whose top-level
module is imported anywhere in ``src``, that module must be resolvable by CI MyPy --
its extra installed by the quality job, or its module in the MyPy ignore list. It is
deterministic and needs no CI run.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _ROOT / "pyproject.toml"
_WORKFLOW = _ROOT / ".github" / "workflows" / "ci.yml"

# Optional-feature extras mapped to the top-level module each one imports.
_EXTRA_IMPORT_MODULE = {
    "visual": "PIL",
    "browser": "playwright",
    "excel": "openpyxl",
    "parquet": "pyarrow",
    "pdf": "reportlab",
}


def _src_imports_module(module: str) -> bool:
    pattern = re.compile(rf"(?:^|\s)(?:import {module}|from {module})\b")
    for path in (_ROOT / "src").rglob("*.py"):
        if pattern.search(path.read_text(encoding="utf-8")):
            return True
    return False


def _mypy_ignored_modules() -> set[str]:
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    ignored: set[str] = set()
    for override in data.get("tool", {}).get("mypy", {}).get("overrides", []):
        if not override.get("ignore_missing_imports"):
            continue
        modules = override.get("module", [])
        for mod in modules if isinstance(modules, list) else [modules]:
            ignored.add(str(mod).split(".", 1)[0])  # "playwright.*" -> "playwright"
    return ignored


def _quality_job_installed_extras() -> set[str]:
    workflow = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    extras: set[str] = set()
    for step in workflow["jobs"]["quality"]["steps"]:
        run = str(step.get("run", ""))
        for group in re.findall(r"\.\[([^\]]+)\]", run):
            extras.update(part.strip() for part in group.split(","))
    return extras


class TestOptionalDependencyTypeCheckContract:
    def test_every_imported_optional_extra_is_resolvable_by_ci_mypy(self) -> None:
        ignored = _mypy_ignored_modules()
        installed = _quality_job_installed_extras()
        unresolved: list[str] = []
        for extra, module in _EXTRA_IMPORT_MODULE.items():
            if not _src_imports_module(module):
                continue
            resolvable = extra in installed or module in ignored
            if not resolvable:
                unresolved.append(f"{extra} (imports {module})")
        assert not unresolved, (
            "Optional-feature imports not resolvable by CI MyPy — install the extra "
            f"in the quality job or add it to mypy ignore_missing_imports: {unresolved}"
        )

    def test_pillow_specifically_is_covered(self) -> None:
        # The exact gap the C3 quality failure hinged on.
        assert _src_imports_module("PIL")
        assert "visual" in _quality_job_installed_extras() or "PIL" in _mypy_ignored_modules()
