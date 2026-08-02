"""Package-level guarantees."""

from __future__ import annotations

import nexusai


def test_the_version_is_exposed() -> None:
    assert nexusai.__version__.count(".") == 2


def test_the_package_is_typed() -> None:
    from pathlib import Path

    # Without py.typed, consumers get no type information from the distribution.
    assert (Path(nexusai.__file__).parent / "py.typed").exists()
