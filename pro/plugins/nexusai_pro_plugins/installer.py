"""Lifecycle operations on plugin distributions via pip.

Plugins are ordinary pip distributions that expose ``nexusai.plugins`` entry points
(ADR-0002), so install/update/remove are pip operations against the active
environment. The command runner is injectable so the manager can be tested without
touching the environment; the default runs ``python -m pip``.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Protocol

from .models import OperationResult


class CommandRunner(Protocol):
    def run(self, args: list[str]) -> tuple[int, str, str]: ...


class PipRunner:
    """Runs ``python -m pip`` and captures the result."""

    def __init__(self, *, timeout: float = 600.0) -> None:
        self._timeout = timeout

    def run(self, args: list[str]) -> tuple[int, str, str]:
        proc = subprocess.run(  # noqa: S603 - fixed executable, controlled args
            [sys.executable, "-m", "pip", *args],
            capture_output=True,
            text=True,
            timeout=self._timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr


class PluginInstaller:
    """Install, update and remove plugin distributions."""

    def __init__(self, runner: CommandRunner | None = None) -> None:
        self._runner = runner or PipRunner()

    def install(self, spec: str, *, version: str | None = None) -> OperationResult:
        """Install a plugin distribution. ``spec`` is any pip requirement.

        A specific version can be requested via ``version`` or embedded in ``spec``
        (e.g. ``my-plugin==1.2.0``), which is how version management is expressed.
        """
        requirement = f"{spec}=={version}" if version else spec
        code, out, err = self._runner.run(["install", requirement])
        return self._result(code, "install", requirement, out, err)

    def update(self, distribution: str, *, version: str | None = None) -> OperationResult:
        """Upgrade a distribution to the latest (or a specific) version."""
        if version:
            code, out, err = self._runner.run(["install", f"{distribution}=={version}"])
            target = f"{distribution}=={version}"
        else:
            code, out, err = self._runner.run(["install", "--upgrade", distribution])
            target = distribution
        return self._result(code, "update", target, out, err)

    def remove(self, distribution: str) -> OperationResult:
        code, out, err = self._runner.run(["uninstall", "-y", distribution])
        return self._result(code, "remove", distribution, out, err)

    @staticmethod
    def _result(code: int, action: str, target: str, out: str, err: str) -> OperationResult:
        ok = code == 0
        message = f"{action} {'succeeded' if ok else 'failed'} for {target}"
        return OperationResult(ok=ok, action=action, target=target, message=message, stdout=out, stderr=err)
