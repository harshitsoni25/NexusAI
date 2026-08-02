"""Mechanical enforcement of the Clean Architecture dependency rules.

Rules that are not enforced mechanically are eventually violated. These tests
encode the allowed and forbidden dependency tables from the Phase 1 architecture
document, so that a developer who crosses a boundary learns it from a failing
build in minutes rather than from a reviewer's opinion in days.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

import nexusai

SOURCE_ROOT = Path(nexusai.__file__).parent
PACKAGE = "nexusai"

# Which internal packages each layer may import. Every layer may also import
# modules directly under ``nexusai`` itself, such as ``__about__``.
ALLOWED_IMPORTS: dict[str, frozenset[str]] = {
    "shared": frozenset(),
    "domain": frozenset({"shared", "domain"}),
    "application": frozenset({"shared", "domain", "application"}),
    "infrastructure": frozenset({"shared", "domain", "infrastructure"}),
    "presentation": frozenset({"shared", "domain", "application", "composition", "presentation"}),
    "composition": frozenset({"shared", "domain", "application", "infrastructure", "composition"}),
    "testing": frozenset({"shared", "domain", "testing"}),
}

# Layers whose purity is the point: no third-party runtime dependency at all.
PURE_LAYERS = ("domain", "shared")

# Specific forbidden edges that the coarse table above would otherwise permit.
FORBIDDEN_EDGES: tuple[tuple[str, str], ...] = (
    # Business decisions must not be made in the presentation layer; it reaches
    # policy through the application layer instead.
    ("presentation", "domain.policy"),
)


def source_files() -> Iterator[Path]:
    """Every Python module in the distributed package."""
    return (path for path in SOURCE_ROOT.rglob("*.py") if "__pycache__" not in path.parts)


def module_name(path: Path) -> str:
    """Return the dotted module name for a source file."""
    relative = path.relative_to(SOURCE_ROOT).with_suffix("")
    parts = [part for part in relative.parts if part != "__init__"]
    return ".".join([PACKAGE, *parts])


def layer_of(module: str) -> str | None:
    """Return the layer a module belongs to, or ``None`` for the package root."""
    parts = module.split(".")
    return parts[1] if len(parts) > 1 and parts[1] in ALLOWED_IMPORTS else None


def imported_modules(path: Path) -> Iterator[str]:
    """Yield every module imported by ``path``, as written."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


def internal_imports(path: Path) -> Iterator[str]:
    """Yield only the imports that point back into this package."""
    for imported in imported_modules(path):
        if imported == PACKAGE or imported.startswith(f"{PACKAGE}."):
            yield imported


def test_the_package_is_discoverable() -> None:
    assert list(source_files()), "no source files found; the layout assumption is wrong"


@pytest.mark.parametrize("path", sorted(source_files()), ids=module_name)
def test_a_module_imports_only_from_permitted_layers(path: Path) -> None:
    module = module_name(path)
    layer = layer_of(module)
    if layer is None:
        return
    allowed = ALLOWED_IMPORTS[layer]
    for imported in internal_imports(path):
        target = layer_of(imported)
        if target is None or target == layer:
            continue
        assert target in allowed, (
            f"{module} (layer '{layer}') imports {imported} (layer '{target}'). "
            f"'{layer}' may only import: {sorted(allowed) or 'the standard library'}."
        )


@pytest.mark.parametrize("path", sorted(source_files()), ids=module_name)
def test_specific_forbidden_edges_are_absent(path: Path) -> None:
    module = module_name(path)
    layer = layer_of(module)
    for source_layer, forbidden_prefix in FORBIDDEN_EDGES:
        if layer != source_layer:
            continue
        for imported in internal_imports(path):
            assert not imported.startswith(f"{PACKAGE}.{forbidden_prefix}"), (
                f"{module} imports {imported}, but '{source_layer}' must not depend on "
                f"'{forbidden_prefix}'."
            )


@pytest.mark.parametrize("path", sorted(source_files()), ids=module_name)
def test_the_pure_layers_have_no_third_party_dependencies(path: Path) -> None:
    """The single most consequential rule, and the one most likely to be broken.

    Keeping the domain free of Pydantic, Loguru, SQLAlchemy and httpx is what
    makes business logic testable without network access, a browser or a
    filesystem.
    """
    module = module_name(path)
    if layer_of(module) not in PURE_LAYERS:
        return
    for imported in imported_modules(path):
        root = imported.split(".")[0]
        if root == PACKAGE or root in sys.stdlib_module_names:
            continue
        raise AssertionError(
            f"{module} imports the third-party package {root!r}. "
            f"Layers {PURE_LAYERS} must depend on the standard library only."
        )


def test_there_are_no_circular_imports() -> None:
    """Cycles are a build failure, not a code review comment."""
    graph = {module_name(path): set(internal_imports(path)) for path in source_files()}
    resolved = {
        module: {target for target in targets if target in graph}
        for module, targets in graph.items()
    }

    visiting: set[str] = set()
    visited: set[str] = set()
    cycles: list[list[str]] = []

    def walk(node: str, trail: list[str]) -> None:
        if node in visiting:
            cycles.append([*trail[trail.index(node) :], node])
            return
        if node in visited:
            return
        visiting.add(node)
        for target in sorted(resolved[node]):
            walk(target, [*trail, node])
        visiting.discard(node)
        visited.add(node)

    for module in sorted(resolved):
        walk(module, [])

    assert not cycles, "circular imports found: " + "; ".join(" -> ".join(c) for c in cycles)


def test_no_module_reaches_for_the_loguru_singleton_outside_its_adapter() -> None:
    """Only the logging adapter may touch Loguru; everything else uses the port."""
    offenders = [
        module_name(path)
        for path in source_files()
        if any(imported.split(".")[0] == "loguru" for imported in imported_modules(path))
    ]
    assert offenders == ["nexusai.infrastructure.observability.logging"]
