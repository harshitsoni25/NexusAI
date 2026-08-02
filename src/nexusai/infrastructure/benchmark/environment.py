"""Capturing the environment a benchmark runs in.

A benchmark number is meaningless without the machine it was taken on, so every
run is stamped with a fingerprint: the interpreter, the platform and
architecture, the CPU count, the framework version and the versions of the
dependencies whose performance matters. This reads the environment through the
standard library and :mod:`importlib.metadata`; it introduces no dependency of its
own.
"""

from __future__ import annotations

import os
import platform
import sys
from importlib import metadata

from nexusai.__about__ import __version__
from nexusai.domain.observability.benchmark import EnvironmentFingerprint

_TRACKED = ("sqlalchemy", "lxml", "httpx", "pydantic")


def capture_environment() -> EnvironmentFingerprint:
    """Capture the current environment as a comparable fingerprint."""
    dependencies: dict[str, str] = {}
    for name in _TRACKED:
        try:
            dependencies[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            dependencies[name] = "absent"
    return EnvironmentFingerprint(
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        machine=platform.machine(),
        cpu_count=os.cpu_count(),
        framework_version=__version__,
        dependencies=dependencies,
    )
