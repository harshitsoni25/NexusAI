"""Phase 6 boundary rules: persistence, export and reporting stay separate.

The coarse layer table permits any infrastructure module to import any other, but
Phase 6 requires finer separation *within* infrastructure: an exporter is not a
persistence client, a report renderer does not read the ORM, and the persistence
layer does not reach back into retrieval or extraction. These rules are enforced
here by inspecting the import graph at the sub-package level, so a boundary
violation fails the build rather than waiting for review.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

import nexusai

SOURCE_ROOT = Path(nexusai.__file__).parent
PACKAGE = "nexusai"

# (source sub-package prefix, forbidden imported prefix, why).
FORBIDDEN: tuple[tuple[str, str, str], ...] = (
    (
        "nexusai.infrastructure.export",
        "nexusai.infrastructure.persistence",
        "an exporter must not depend on persistence (SQLite/SQLAlchemy)",
    ),
    (
        "nexusai.infrastructure.reporting",
        "nexusai.infrastructure.persistence",
        "a report renderer must not depend on the ORM",
    ),
    (
        "nexusai.infrastructure.export",
        "nexusai.application.processing",
        "export must not re-run Phase 5 processing",
    ),
    (
        "nexusai.infrastructure.reporting",
        "nexusai.application.processing",
        "reporting must not recalculate Phase 5 results",
    ),
    (
        "nexusai.infrastructure.persistence",
        "nexusai.infrastructure.retrieval",
        "persistence must not invoke retrieval",
    ),
    (
        "nexusai.infrastructure.persistence",
        "nexusai.infrastructure.extraction",
        "persistence must not invoke extraction",
    ),
    (
        "nexusai.domain",
        "sqlalchemy",
        "the domain must never import SQLAlchemy",
    ),
)


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
def test_downstream_subpackage_boundaries(path: Path) -> None:
    module = _module_name(path)
    for source_prefix, forbidden_prefix, reason in FORBIDDEN:
        if not module.startswith(source_prefix):
            continue
        for imported in _imports(path):
            assert imported != forbidden_prefix and not imported.startswith(
                f"{forbidden_prefix}."
            ), f"{module} imports {imported}: {reason}."
