"""Phase 7 boundary: presentation is a leaf; the orchestrator stays pure.

Clean Architecture points dependencies inward, and two consequences matter most
once a presentation layer and an orchestrator exist. First, nothing below
presentation may import it: the domain, application and infrastructure must not
depend on the CLI, or the CLI stops being replaceable. Second, the workflow
orchestrator coordinates but does not do the work, so it must not reach into
infrastructure. Both rules are enforced here by inspecting the import graph.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

import nexusai

SOURCE_ROOT = Path(nexusai.__file__).parent
PACKAGE = "nexusai"


def _source_files() -> list[Path]:
    return sorted(path for path in SOURCE_ROOT.rglob("*.py") if "__pycache__" not in path.parts)


def _module_name(path: Path) -> str:
    relative = path.relative_to(SOURCE_ROOT).with_suffix("")
    parts = [part for part in relative.parts if part != "__init__"]
    return ".".join([PACKAGE, *parts])


def _imports(path: Path) -> Iterator[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


@pytest.mark.parametrize("path", _source_files(), ids=_module_name)
def test_presentation_is_not_imported_by_lower_layers(path: Path) -> None:
    module = _module_name(path)
    layer = module.split(".")[1] if module.count(".") >= 1 else ""
    if layer not in {"domain", "application", "infrastructure"}:
        return
    for imported in _imports(path):
        assert not imported.startswith(
            "nexusai.presentation"
        ), f"{module} imports {imported}: lower layers must not depend on presentation."


@pytest.mark.parametrize("path", _source_files(), ids=_module_name)
def test_orchestrator_does_not_import_infrastructure(path: Path) -> None:
    module = _module_name(path)
    if not module.startswith("nexusai.application.workflow"):
        return
    for imported in _imports(path):
        assert not imported.startswith("nexusai.infrastructure"), (
            f"{module} imports {imported}: the orchestrator coordinates, "
            "it does not reach into infrastructure."
        )
