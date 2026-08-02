"""Security: the production tree uses no unsafe deserialization or dynamic exec."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.security

_SRC = Path(__file__).resolve().parents[2] / "src" / "nexusai"
_FORBIDDEN_CALLS = {"eval", "exec", "compile"}
_FORBIDDEN_ATTRS = {("pickle", "load"), ("pickle", "loads"), ("marshal", "loads")}


def _python_files() -> list[Path]:
    return [p for p in _SRC.rglob("*.py") if "__pycache__" not in p.parts]


class TestNoUnsafePrimitives:
    def test_no_eval_exec_compile_or_pickle(self) -> None:
        offenders: list[str] = []
        for path in _python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name) and func.id in _FORBIDDEN_CALLS:
                        offenders.append(f"{path.name}: {func.id}()")
                    if (
                        isinstance(func, ast.Attribute)
                        and isinstance(func.value, ast.Name)
                        and (func.value.id, func.attr) in _FORBIDDEN_ATTRS
                    ):
                        offenders.append(f"{path.name}: {func.value.id}.{func.attr}()")
        assert not offenders, f"unsafe primitives found: {offenders}"

    def test_yaml_is_loaded_safely(self) -> None:
        offenders: list[str] = []
        for path in _python_files():
            text = path.read_text(encoding="utf-8")
            if "yaml.load(" in text and "SafeLoader" not in text:
                offenders.append(path.name)
        assert not offenders, f"unsafe yaml.load found: {offenders}"
