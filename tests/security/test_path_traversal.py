"""Security: output paths cannot escape their approved root."""

from __future__ import annotations

from pathlib import Path

import pytest

from nexusai.domain.errors.exceptions import StorageError
from nexusai.infrastructure.artifacts.paths import safe_join

pytestmark = pytest.mark.security


class TestSafeJoin:
    def test_plain_name_resolves_under_base(self, tmp_path: Path) -> None:
        assert safe_join(tmp_path, "report.html").parent == tmp_path

    @pytest.mark.parametrize(
        "name",
        [
            "../escape.txt",
            "../../etc/passwd",
            "sub/../../escape.txt",
            "a/b/../../../c.txt",
        ],
    )
    def test_traversal_is_rejected(self, tmp_path: Path, name: str) -> None:
        with pytest.raises(StorageError):
            safe_join(tmp_path, name)

    @pytest.mark.parametrize("name", ["/etc/passwd", "/tmp/abs.txt"])
    def test_absolute_paths_rejected(self, tmp_path: Path, name: str) -> None:
        with pytest.raises(StorageError):
            safe_join(tmp_path, name)

    def test_empty_name_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(StorageError):
            safe_join(tmp_path, "")

    def test_nested_subdir_allowed(self, tmp_path: Path) -> None:
        result = safe_join(tmp_path, "sub/dir/file.csv")
        assert str(result).startswith(str(tmp_path))
