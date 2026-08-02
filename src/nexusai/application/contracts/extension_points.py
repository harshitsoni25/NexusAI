"""A read-only view of the framework's published extension points.

The presentation layer needs this to answer "what can I extend, and against
which contract version?". It reaches the answer through the application layer
rather than importing the domain policy directly, so that a future REST API
answering the same question shares one implementation rather than duplicating
the traversal.
"""

from __future__ import annotations

from dataclasses import dataclass

from nexusai.domain.model.plugin import ApiVersion, ExtensionPoint
from nexusai.domain.policy.plugin_compatibility import SUPPORTED_API_VERSIONS


@dataclass(frozen=True, slots=True)
class ExtensionPointDescription:
    """One extension point and the contract version this framework provides."""

    extension_point: ExtensionPoint
    supported_api_version: ApiVersion

    @property
    def name(self) -> str:
        """The stable identifier a plugin declares."""
        return self.extension_point.value


def describe_extension_points() -> tuple[ExtensionPointDescription, ...]:
    """Return every extension point, ordered by name for stable display."""
    return tuple(
        sorted(
            (
                ExtensionPointDescription(point, version)
                for point, version in SUPPORTED_API_VERSIONS.items()
            ),
            key=lambda item: item.name,
        )
    )
