"""Deep merging of configuration layers, with origin tracking.

Origin tracking exists so that a validation failure can name not just the
offending key but the file, environment variable or command-line flag that
supplied it. Telling an operator that ``logging.level`` is invalid is far less
useful than telling them it was set to ``VERBOSE`` by ``config/production.yaml``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from nexusai.infrastructure.config.sources import ConfigSource
from nexusai.shared.types import MutableJsonMapping


@dataclass(frozen=True, slots=True)
class MergedConfiguration:
    """The result of merging every configuration layer.

    Attributes:
        values: The merged configuration.
        origins: Dotted key to the name of the source that last set it.
    """

    values: MutableJsonMapping
    origins: Mapping[str, str]

    def origin_of(self, dotted_key: str) -> str | None:
        """Return the source that supplied ``dotted_key``.

        Falls back to the nearest configured ancestor, because a key that was
        never explicitly set still has a meaningful origin: whichever layer
        established the mapping it lives in.
        """
        if dotted_key in self.origins:
            return self.origins[dotted_key]
        segments = dotted_key.split(".")
        for cut in range(len(segments) - 1, 0, -1):
            ancestor = ".".join(segments[:cut])
            if ancestor in self.origins:
                return self.origins[ancestor]
        return None


def merge_sources(sources: Sequence[ConfigSource]) -> MergedConfiguration:
    """Merge ``sources`` in ascending order of precedence.

    Later sources override earlier ones. Mappings are merged recursively;
    scalars and sequences are replaced wholesale, because a partial override of
    a list has no unambiguous meaning.

    Args:
        sources: Layers ordered lowest precedence first.
    """
    values: MutableJsonMapping = {}
    origins: dict[str, str] = {}
    for source in sources:
        _merge_into(values, source.load(), origins, source.name, prefix="")
    return MergedConfiguration(values=values, origins=origins)


def _merge_into(
    target: MutableJsonMapping,
    incoming: Mapping[str, Any],
    origins: dict[str, str],
    source_name: str,
    prefix: str,
) -> None:
    for key, value in incoming.items():
        dotted = f"{prefix}{key}"
        existing = target.get(key)
        if isinstance(value, Mapping) and isinstance(existing, dict):
            origins[dotted] = source_name
            _merge_into(existing, value, origins, source_name, prefix=f"{dotted}.")
        elif isinstance(value, Mapping):
            nested: MutableJsonMapping = {}
            target[key] = nested
            origins[dotted] = source_name
            _merge_into(nested, value, origins, source_name, prefix=f"{dotted}.")
        else:
            target[key] = value
            origins[dotted] = source_name
