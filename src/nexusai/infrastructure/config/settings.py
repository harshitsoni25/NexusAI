"""Strongly typed configuration schema.

Pydantic is used here and not in the domain layer (ADR-0004): validation belongs
where untrusted data enters the system. Once configuration has been validated it
is frozen, and every component receives it by constructor injection. No
component reads configuration at point of use -- that would reintroduce the
global state section 8 prohibits and make components untestable without a
configuration file.

Only framework-level settings appear here. Scraping, storage, export and
reporting settings are added by the phases that own those components.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

_STRICT = ConfigDict(frozen=True, extra="forbid", validate_default=True, use_enum_values=False)
"""Shared model configuration.

``extra="forbid"`` matters more than it looks: it turns a misspelled YAML key
into an immediate, named error instead of a silently ignored setting that leaves
an operator wondering why their change had no effect.
"""


class Environment(Enum):
    """Where the framework is running."""

    LOCAL = "local"
    CI = "ci"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(Enum):
    """Severity threshold for a logging sink."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """How log records are rendered."""

    CONSOLE = "console"
    """Human-readable, for interactive use."""

    JSON = "json"
    """One JSON object per line, for log aggregation."""


class ConsoleLogSettings(BaseModel):
    """Console sink configuration."""

    model_config = _STRICT

    enabled: bool = True
    level: LogLevel = LogLevel.INFO
    format: LogFormat = LogFormat.CONSOLE
    colorize: bool = True


class FileLogSettings(BaseModel):
    """Rotating file sink configuration."""

    model_config = _STRICT

    enabled: bool = False
    filename: str = "nexusai.log"
    level: LogLevel = LogLevel.DEBUG
    format: LogFormat = LogFormat.JSON
    rotation: str = Field(default="20 MB", description="Loguru rotation policy.")
    retention: str = Field(default="14 days", description="Loguru retention policy.")
    compression: str | None = "gz"


class LoggingSettings(BaseModel):
    """Logging configuration.

    ``level`` is the floor applied before any sink is consulted, which is what
    makes ``--verbose`` a single switch rather than a per-sink adjustment.
    """

    model_config = _STRICT

    level: LogLevel = LogLevel.INFO
    console: ConsoleLogSettings = ConsoleLogSettings()
    file: FileLogSettings = FileLogSettings()
    include_correlation: bool = True
    diagnose: bool = Field(
        default=False,
        description=(
            "Include variable values in tracebacks. Off by default because those "
            "values can contain secrets, and this output frequently ends up in "
            "shared log aggregation."
        ),
    )


class PathSettings(BaseModel):
    """Filesystem locations the framework writes to.

    Every path is relative to ``root`` unless given as absolute, so a whole
    deployment can be relocated by changing one setting.
    """

    model_config = _STRICT

    root: Path = Path("./.nexusai")
    data: Path = Path("data")
    artifacts: Path = Path("artifacts")
    reports: Path = Path("reports")
    logs: Path = Path("logs")
    state: Path = Path("state")

    def resolve(self, name: str) -> Path:
        """Return an absolute path for one of the configured directories.

        Args:
            name: One of ``data``, ``artifacts``, ``reports``, ``logs``, ``state``.

        Raises:
            ValueError: If ``name`` is not a configured directory.
        """
        if name not in {"data", "artifacts", "reports", "logs", "state"}:
            raise ValueError(f"Unknown path {name!r}")
        value: Path = getattr(self, name)
        if value.is_absolute():
            return value
        return (self.root / value).resolve()


class PluginSettings(BaseModel):
    """Plugin discovery configuration.

    Discovery is restricted to installed entry points plus an explicit
    allow-list of module paths. Scanning arbitrary directories for Python files
    is deliberately not supported: it executes untrusted code found on disk,
    which is a security defect in a system intended to run unattended (ADR-0006).
    """

    model_config = _STRICT

    discovery_enabled: bool = True
    entry_point_group: str = "nexusai.plugins"
    allowlist: tuple[str, ...] = ()
    disabled: tuple[str, ...] = ()
    fail_on_load_error: bool = Field(
        default=False,
        description=(
            "Abort startup when a plugin fails to load. Off by default so that "
            "one broken third-party plugin cannot prevent the framework from "
            "running; production deployments may prefer to turn it on."
        ),
    )


class FrameworkSettings(BaseModel):
    """The complete, validated configuration for a single execution."""

    model_config = _STRICT

    environment: Environment = Environment.LOCAL
    paths: PathSettings = PathSettings()
    logging: LoggingSettings = LoggingSettings()
    plugins: PluginSettings = PluginSettings()
