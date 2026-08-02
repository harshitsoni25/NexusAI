"""The version gate applied to every plugin before registration.

This is pure decision logic over pure data -- no I/O, no third-party library --
so it belongs in the domain alongside the other policies, not in the loader that
happens to invoke it.

Each extension point carries its own API version, independent of the framework
release version. A breaking change to the exporter contract therefore does not
invalidate every site adapter in existence -- a property that matters greatly
once external teams depend on the framework, and one that is close to impossible
to retrofit later.
"""

from __future__ import annotations

from collections.abc import Mapping

from nexusai.domain.errors import PluginContractError
from nexusai.domain.model.plugin import ApiVersion, ExtensionPoint, PluginMetadata

SUPPORTED_API_VERSIONS: Mapping[ExtensionPoint, ApiVersion] = {
    point: ApiVersion(1, 0) for point in ExtensionPoint
}
"""The contract version the running framework provides for each extension point.

Every point starts at 1.0. Points advance independently as their contracts gain
members; a point only reaches 2.0 if its contract takes a breaking change, which
requires a deprecation window first.
"""


def supported_version(extension_point: ExtensionPoint) -> ApiVersion:
    """Return the contract version this framework provides for ``extension_point``."""
    return SUPPORTED_API_VERSIONS[extension_point]


def assert_compatible(metadata: PluginMetadata) -> None:
    """Verify that a plugin's target contract version is satisfiable.

    Raises:
        PluginContractError: If the plugin targets a different major version, or
            a later minor version than the framework provides.
    """
    supported = supported_version(metadata.extension_point)
    if metadata.api_version.is_compatible_with(supported):
        return
    if metadata.api_version.major != supported.major:
        reason = (
            f"targets contract major version {metadata.api_version.major}, "
            f"but this framework provides {supported.major}"
        )
    else:
        reason = (
            f"targets contract version {metadata.api_version}, which is newer than the "
            f"{supported} this framework provides; upgrade Nexus AI or use an earlier "
            "release of the plugin"
        )
    raise PluginContractError(
        f"Plugin {metadata.qualified_name!r} is not compatible: {reason}",
        plugin=metadata.qualified_name,
        plugin_api_version=str(metadata.api_version),
        supported_api_version=str(supported),
    )
