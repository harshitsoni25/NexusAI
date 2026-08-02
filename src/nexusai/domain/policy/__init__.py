"""Pure decision logic: the part of the system that decides rather than acts.

Every module here is a pure function of its inputs, executable in a unit test
with no network, no browser and no filesystem. Quality scoring, validation
thresholds, change significance and strategy recommendation join the plugin
compatibility rule as each engine is introduced.
"""

from __future__ import annotations

from nexusai.domain.policy.plugin_compatibility import (
    SUPPORTED_API_VERSIONS,
    assert_compatible,
    supported_version,
)

__all__ = ["SUPPORTED_API_VERSIONS", "assert_compatible", "supported_version"]
