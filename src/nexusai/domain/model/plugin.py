"""Value objects describing a plugin and the point it extends."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Self

_VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)$")


class ExtensionPoint(Enum):
    """The categories of extension the framework publishes.

    Each point carries its own API version, independent of the framework release
    version, so that a breaking change to one contract does not invalidate every
    plugin implementing the others.
    """

    SITE_ADAPTER = "site_adapter"
    SCRAPING_STRATEGY = "scraping_strategy"
    EXTRACTOR = "extractor"
    VALIDATOR = "validator"
    DQA_RULE = "dqa_rule"
    EXPORTER = "exporter"
    STORAGE_PROVIDER = "storage_provider"
    REPORT_GENERATOR = "report_generator"
    MIDDLEWARE = "middleware"
    NOTIFICATION = "notification"


@dataclass(frozen=True, slots=True, order=True)
class ApiVersion:
    """A two-part contract version: ``major.minor``.

    Patch numbers are absent by design. A contract has no implementation to fix,
    so only two kinds of change exist: additive (minor) and breaking (major).
    """

    major: int
    minor: int

    def __post_init__(self) -> None:
        if self.major < 0 or self.minor < 0:
            raise ValueError(f"Version components must be non-negative, got {self}")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"

    @classmethod
    def parse(cls, raw: str) -> Self:
        """Parse ``major.minor`` from a string.

        Raises:
            ValueError: If ``raw`` is not exactly two dot-separated integers.
        """
        match = _VERSION_PATTERN.match(raw.strip())
        if match is None:
            raise ValueError(f"Invalid API version {raw!r}; expected the form 'major.minor'")
        return cls(int(match.group(1)), int(match.group(2)))

    def is_compatible_with(self, supported: ApiVersion) -> bool:
        """Whether a plugin targeting this version works against ``supported``.

        Compatibility follows from the contract evolution rule: within a major
        version, changes are additive only. A plugin written against an earlier
        minor version therefore still satisfies a later one, but a plugin written
        against a *later* minor may rely on members the running framework does
        not yet provide.
        """
        return self.major == supported.major and self.minor <= supported.minor


@dataclass(frozen=True, slots=True)
class PluginMetadata:
    """Self-description supplied by every plugin.

    Attributes:
        name: Unique identifier within its extension point.
        version: The plugin's own release version, opaque to the framework.
        extension_point: Which contract the plugin implements.
        api_version: The contract version the plugin was written against.
        description: One-line summary shown by the ``plugins`` command.
        author: Responsible party, useful when a third-party plugin misbehaves.
    """

    name: str
    version: str
    extension_point: ExtensionPoint
    api_version: ApiVersion
    description: str = ""
    author: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Plugin name must not be empty")
        if not self.version.strip():
            raise ValueError(f"Plugin {self.name!r} must declare a version")

    @property
    def qualified_name(self) -> str:
        """``extension_point:name``, unique across the whole registry."""
        return f"{self.extension_point.value}:{self.name}"
