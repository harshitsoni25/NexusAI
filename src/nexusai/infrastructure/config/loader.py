"""Assembly and validation of the configuration precedence chain."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values
from pydantic import ValidationError as PydanticValidationError

from nexusai.domain.errors import ConfigurationError
from nexusai.infrastructure.config.merger import MergedConfiguration, merge_sources
from nexusai.infrastructure.config.settings import FrameworkSettings
from nexusai.infrastructure.config.sources import (
    CliOverrideSource,
    ConfigSource,
    DefaultsSource,
    EnvironmentSource,
    YamlFileSource,
)

DEFAULT_CONFIG_FILENAME = "config/default.yaml"
DEFAULT_DOTENV_FILENAME = ".env"


@dataclass(frozen=True, slots=True)
class LoadedConfiguration:
    """A validated configuration together with the trail that produced it.

    The merged values and their origins are retained so that ``nexusai config
    show`` can explain where every effective setting came from, and so that the
    full effective configuration can be recorded against a run for auditability.
    """

    settings: FrameworkSettings
    merged: MergedConfiguration
    source_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConfigurationLoader:
    """Builds the precedence chain and validates the result.

    Precedence, highest first: command-line overrides, environment variables,
    an explicitly supplied YAML file, the packaged default file, and the field
    defaults declared on the settings models.

    Args:
        packaged_defaults: Optional YAML file shipped with the project.
        defaults: Values supplied in code, beneath every file.
    """

    packaged_defaults: Path | None = Path(DEFAULT_CONFIG_FILENAME)
    defaults: Mapping[str, object] = field(default_factory=dict)

    def build_sources(
        self,
        *,
        config_file: Path | None = None,
        overrides: Sequence[str] = (),
        environ: Mapping[str, str] | None = None,
        dotenv_path: Path | None = None,
    ) -> tuple[ConfigSource, ...]:
        """Return the chain of sources, ordered lowest precedence first."""
        import os

        sources: list[ConfigSource] = [DefaultsSource(self.defaults)]
        if self.packaged_defaults is not None:
            sources.append(YamlFileSource(self.packaged_defaults, required=False))
        if config_file is not None:
            sources.append(YamlFileSource(config_file, required=True))

        resolved_environ = dict(os.environ if environ is None else environ)
        dotenv_file = dotenv_path or Path(DEFAULT_DOTENV_FILENAME)
        if dotenv_file.exists():
            # Real environment variables win over the .env file, which is a
            # developer convenience rather than a deployment mechanism.
            from_file = {k: v for k, v in dotenv_values(dotenv_file).items() if v is not None}
            resolved_environ = {**from_file, **resolved_environ}
        sources.append(EnvironmentSource(resolved_environ))

        if overrides:
            sources.append(CliOverrideSource(tuple(overrides)))
        return tuple(sources)

    def load(
        self,
        *,
        config_file: Path | None = None,
        overrides: Sequence[str] = (),
        environ: Mapping[str, str] | None = None,
        dotenv_path: Path | None = None,
    ) -> LoadedConfiguration:
        """Resolve, merge and validate the configuration.

        Raises:
            ConfigurationError: If any layer is unreadable or the merged result
                fails validation. The message names every offending key, the
                source that supplied it, and what was expected instead.
        """
        sources = self.build_sources(
            config_file=config_file,
            overrides=overrides,
            environ=environ,
            dotenv_path=dotenv_path,
        )
        merged = merge_sources(sources)
        try:
            settings = FrameworkSettings.model_validate(merged.values)
        except PydanticValidationError as exc:
            raise _as_configuration_error(exc, merged) from exc
        return LoadedConfiguration(
            settings=settings,
            merged=merged,
            source_names=tuple(source.name for source in sources),
        )


def _as_configuration_error(
    error: PydanticValidationError, merged: MergedConfiguration
) -> ConfigurationError:
    """Translate a Pydantic failure into an actionable framework error."""
    lines: list[str] = []
    keys: list[str] = []
    for detail in error.errors():
        dotted = ".".join(str(part) for part in detail["loc"])
        keys.append(dotted)
        origin = merged.origin_of(dotted) or "unknown source"
        provided = detail.get("input")
        lines.append(f"  - {dotted}: {detail['msg']} (got {provided!r}, set by {origin})")
    summary = "Configuration is invalid:\n" + "\n".join(lines)
    return ConfigurationError(summary, invalid_keys=tuple(sorted(keys)))
