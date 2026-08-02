"""Per-invocation command line state.

Held on the Typer context rather than in a module-level variable, so that
concurrent or repeated invocations in one process cannot observe each other's
configuration -- and so that the CLI keeps the framework's own prohibition on
shared mutable global state.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from nexusai.composition.container import Container, bootstrap


@dataclass(slots=True)
class CliState:
    """Global options captured before any command runs.

    The container is built lazily. ``nexusai --version`` should not read
    configuration files or discover plugins in order to print a version string.
    """

    config_file: Path | None = None
    overrides: tuple[str, ...] = ()
    _container: Container | None = field(default=None, repr=False)

    def container(self) -> Container:
        """Return the wired container, building it on first use."""
        if self._container is None:
            self._container = bootstrap(config_file=self.config_file, overrides=self.overrides)
        return self._container

    @property
    def is_built(self) -> bool:
        """Whether the container has been constructed for this invocation."""
        return self._container is not None


def resolve_overrides(log_level: str | None, verbose: bool, quiet: bool) -> Sequence[str]:
    """Translate verbosity flags into configuration overrides.

    Routing ``--verbose`` through the ordinary override mechanism rather than a
    special case means the flag obeys the documented precedence chain, and there
    is exactly one code path that decides the effective log level.
    """
    if quiet and verbose:
        from nexusai.domain.errors import ConfigurationError

        raise ConfigurationError("--quiet and --verbose cannot be used together")
    if log_level is not None:
        return (f"logging.level={log_level.upper()}", f"logging.console.level={log_level.upper()}")
    if verbose:
        return ("logging.level=DEBUG", "logging.console.level=DEBUG")
    if quiet:
        return ("logging.level=ERROR", "logging.console.level=ERROR")
    return ()
