"""The doctor use case: environment readiness checks.

Doctor answers "is this environment ready to run?" as a list of independent
checks, each reporting PASS, WARNING or FAIL with a short remediation hint. It
reads only what it needs -- the Python version, the presence of directories and
optional dependencies, the plugin and adapter registries -- and it never prints or
returns a secret. A WARNING means degraded-but-usable (an optional export format
is unavailable); a FAIL means something required is missing.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from importlib import util as import_util


class CheckStatus(Enum):
    """The outcome of one readiness check."""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass(frozen=True, slots=True, kw_only=True)
class Check:
    """One readiness check result."""

    name: str
    status: CheckStatus
    detail: str = ""
    remediation: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {
            "name": self.name,
            "status": self.status.value,
            "detail": self.detail,
            "remediation": self.remediation,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class DoctorReport:
    """The full set of readiness checks and an overall verdict."""

    checks: Sequence[Check]

    @property
    def ok(self) -> bool:
        """Whether no check failed."""
        return all(c.status is not CheckStatus.FAIL for c in self.checks)

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {"ok": self.ok, "checks": [c.to_dict() for c in self.checks]}


class DoctorUseCase:
    """Runs environment readiness checks."""

    def __init__(
        self,
        *,
        adapter_names: Sequence[str] = (),
        plugin_count: int = 0,
        min_python: tuple[int, int] = (3, 12),
    ) -> None:
        self._adapter_names = tuple(adapter_names)
        self._plugin_count = plugin_count
        self._min_python = min_python

    def execute(self) -> DoctorReport:
        """Run every check and return the report."""
        checks: list[Check] = [
            self._python(),
            self._optional("openpyxl", "Excel export", "pip install nexusai[excel]"),
            self._optional("pyarrow", "Parquet export", "pip install nexusai[parquet]"),
            self._optional("reportlab", "PDF reporting", "pip install nexusai[pdf]"),
            self._optional("playwright", "browser retrieval", "pip install nexusai[browser]"),
            self._required("sqlalchemy", "persistence"),
            self._adapters(),
            self._plugins(),
        ]
        return DoctorReport(checks=checks)

    def _python(self) -> Check:
        current = sys.version_info[:2]
        if current >= self._min_python:
            return Check(
                name="python-version",
                status=CheckStatus.PASS,
                detail=f"{current[0]}.{current[1]}",
            )
        return Check(
            name="python-version",
            status=CheckStatus.FAIL,
            detail=f"{current[0]}.{current[1]}",
            remediation=f"upgrade to Python {self._min_python[0]}.{self._min_python[1]}+",
        )

    def _optional(self, module: str, feature: str, remediation: str) -> Check:
        available = import_util.find_spec(module) is not None
        return Check(
            name=f"optional:{module}",
            status=CheckStatus.PASS if available else CheckStatus.WARNING,
            detail=f"{feature} {'available' if available else 'unavailable'}",
            remediation="" if available else remediation,
        )

    def _required(self, module: str, feature: str) -> Check:
        available = import_util.find_spec(module) is not None
        return Check(
            name=f"required:{module}",
            status=CheckStatus.PASS if available else CheckStatus.FAIL,
            detail=f"{feature} {'available' if available else 'MISSING'}",
            remediation="" if available else f"reinstall nexusai to restore {module}",
        )

    def _adapters(self) -> Check:
        return Check(
            name="site-adapters",
            status=CheckStatus.PASS if self._adapter_names else CheckStatus.WARNING,
            detail=f"{len(self._adapter_names)} registered",
            remediation="" if self._adapter_names else "register at least one site adapter",
        )

    def _plugins(self) -> Check:
        return Check(
            name="plugin-registry",
            status=CheckStatus.PASS,
            detail=f"{self._plugin_count} plugins registered",
        )
