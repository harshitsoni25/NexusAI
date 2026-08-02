"""Safe path resolution for artefact, export and report output.

Every filesystem write in Phase 6 goes through :func:`safe_join`, which resolves a
caller-supplied name against a configured base directory and refuses anything
that would escape it. This is the single guard against path traversal, absolute
paths, and symlink escapes: a name like ``../../etc/passwd`` or ``/etc/passwd``
raises rather than writing outside the sandbox.

The resolution is done on the fully resolved real paths, so a symlink inside the
base that points outside it is caught too -- the check is on where the path
actually lands, not on how it is spelt.
"""

from __future__ import annotations

from pathlib import Path

from nexusai.domain.errors.exceptions import StorageError


def safe_join(base: Path, name: str) -> Path:
    """Resolve ``name`` under ``base`` and confirm it does not escape.

    Args:
        base: The directory outputs must stay within.
        name: A relative path under ``base``. Absolute paths are rejected.

    Returns:
        The resolved absolute path, guaranteed to be inside ``base``.

    Raises:
        StorageError: If ``name`` is empty, absolute, or resolves outside ``base``.
    """
    if not name or not name.strip():
        raise StorageError("Output name must not be empty")
    candidate = Path(name)
    if candidate.is_absolute():
        raise StorageError("Absolute output paths are not permitted", name=name)

    base_resolved = base.resolve()
    target = (base_resolved / candidate).resolve()
    if base_resolved != target and base_resolved not in target.parents:
        raise StorageError("Output path escapes the permitted directory", name=name)
    return target


def ensure_parent(path: Path) -> None:
    """Create the parent directory of ``path`` if it does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
