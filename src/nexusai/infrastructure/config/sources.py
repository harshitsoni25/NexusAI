"""Configuration sources, one per level of the precedence chain.

Precedence, highest first: CLI overrides, environment variables, YAML files,
built-in defaults. Each source is independently testable and knows nothing about
the others; ordering is applied by the merger.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import yaml

from nexusai.domain.errors import ConfigurationError
from nexusai.shared.types import MutableJsonMapping


@runtime_checkable
class ConfigSource(Protocol):
    """A layer of configuration."""

    @property
    def name(self) -> str:
        """Human-readable origin, quoted back to the user in error messages."""
        ...

    def load(self) -> MutableJsonMapping:
        """Return this layer's values as a nested mapping."""
        ...


@dataclass(frozen=True, slots=True)
class DefaultsSource:
    """The lowest-precedence layer: values supplied in code."""

    values: Mapping[str, Any]

    @property
    def name(self) -> str:
        """Return the label shown when this layer is blamed for a value."""
        return "built-in defaults"

    def load(self) -> MutableJsonMapping:
        """Return the values supplied in code."""
        return dict(self.values)


@dataclass(frozen=True, slots=True)
class YamlFileSource:
    """A YAML configuration file.

    A missing file is only an error when the path was requested explicitly. This
    is what allows a default location to be probed without forcing every
    deployment to create one.
    """

    path: Path
    required: bool = True

    @property
    def name(self) -> str:
        """Return the label shown when this layer is blamed for a value."""
        return f"YAML file {self.path}"

    def load(self) -> MutableJsonMapping:
        """Read and parse the file, returning an empty layer when absent and optional."""
        if not self.path.exists():
            if self.required:
                raise ConfigurationError("Configuration file not found", path=str(self.path))
            return {}
        try:
            raw = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ConfigurationError(
                "Configuration file is not valid YAML", path=str(self.path), detail=str(exc)
            ) from exc
        except OSError as exc:
            raise ConfigurationError(
                "Configuration file could not be read", path=str(self.path), detail=str(exc)
            ) from exc
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ConfigurationError(
                "Configuration file must contain a mapping at the top level",
                path=str(self.path),
                found=type(raw).__name__,
            )
        return dict(raw)


@dataclass(frozen=True, slots=True)
class EnvironmentSource:
    """Environment variables matching a prefix.

    ``NEXUSAI_LOGGING__LEVEL=DEBUG`` becomes ``{"logging": {"level": "DEBUG"}}``.
    A double underscore separates levels of nesting so that single underscores
    remain usable inside key names.

    Values are parsed as YAML scalars, which is what makes ``true``, ``42`` and
    ``null`` arrive as a boolean, an integer and ``None`` rather than as three
    strings that then fail type validation.
    """

    environ: Mapping[str, str]
    prefix: str = "NEXUSAI_"
    nested_delimiter: str = "__"

    @property
    def name(self) -> str:
        """Return the label shown when this layer is blamed for a value."""
        return f"environment variables ({self.prefix}*)"

    def load(self) -> MutableJsonMapping:
        """Collect matching variables and expand them into a nested mapping."""
        result: MutableJsonMapping = {}
        for raw_key, raw_value in self.environ.items():
            if not raw_key.startswith(self.prefix):
                continue
            path = raw_key[len(self.prefix) :].lower().split(self.nested_delimiter)
            if not all(path):
                raise ConfigurationError(
                    "Environment variable has an empty key segment", variable=raw_key
                )
            _assign(result, path, _parse_scalar(raw_value), origin=raw_key)
        return result


@dataclass(frozen=True, slots=True)
class CliOverrideSource:
    """The highest-precedence layer: ``key.path=value`` pairs from the command line."""

    overrides: Sequence[str]

    @property
    def name(self) -> str:
        """Return the label shown when this layer is blamed for a value."""
        return "command line override"

    def load(self) -> MutableJsonMapping:
        """Expand each ``key.path=value`` pair into a nested mapping."""
        result: MutableJsonMapping = {}
        for override in self.overrides:
            key, separator, value = override.partition("=")
            if not separator or not key.strip():
                raise ConfigurationError(
                    "Override must use the form key.path=value", override=override
                )
            path = key.strip().split(".")
            if not all(segment.strip() for segment in path):
                raise ConfigurationError("Override key has an empty segment", override=override)
            _assign(result, [segment.strip() for segment in path], _parse_scalar(value), override)
        return result


def _parse_scalar(raw: str) -> Any:
    """Interpret a string as a YAML scalar, falling back to the string itself."""
    try:
        parsed = yaml.safe_load(raw)
    except yaml.YAMLError:
        return raw
    if isinstance(parsed, (dict, list)):
        return parsed
    return raw if parsed is None and raw.strip() not in {"null", "~", ""} else parsed


def _assign(target: MutableJsonMapping, path: Sequence[str], value: Any, origin: str) -> None:
    """Set a nested key, creating intermediate mappings as required."""
    cursor: Any = target
    for segment in path[:-1]:
        existing = cursor.get(segment)
        if existing is None:
            existing = {}
            cursor[segment] = existing
        elif not isinstance(existing, dict):
            raise ConfigurationError(
                "Override conflicts with an earlier value that is not a mapping",
                key=".".join(path),
                conflicting_segment=segment,
                origin=origin,
            )
        cursor = existing
    cursor[path[-1]] = value
