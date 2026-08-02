"""The plugin version gate."""

from __future__ import annotations

import pytest

from nexusai.domain.errors import PluginContractError
from nexusai.domain.model.plugin import ApiVersion, ExtensionPoint, PluginMetadata
from nexusai.domain.policy.plugin_compatibility import (
    SUPPORTED_API_VERSIONS,
    assert_compatible,
    supported_version,
)


def metadata(api_version: ApiVersion) -> PluginMetadata:
    return PluginMetadata("stub", "1.0.0", ExtensionPoint.EXPORTER, api_version)


def test_every_extension_point_publishes_a_version() -> None:
    # A point without a declared version could never be safely extended.
    assert set(SUPPORTED_API_VERSIONS) == set(ExtensionPoint)


def test_a_matching_version_passes() -> None:
    assert_compatible(metadata(supported_version(ExtensionPoint.EXPORTER)))


def test_an_older_minor_version_passes() -> None:
    assert_compatible(metadata(ApiVersion(1, 0)))


def test_a_newer_minor_version_is_rejected_with_advice() -> None:
    with pytest.raises(PluginContractError, match="upgrade Nexus AI") as caught:
        assert_compatible(metadata(ApiVersion(1, 99)))
    assert caught.value.context["plugin_api_version"] == "1.99"


def test_a_different_major_version_is_rejected_as_breaking() -> None:
    with pytest.raises(PluginContractError, match="major version"):
        assert_compatible(metadata(ApiVersion(2, 0)))


def test_the_error_names_the_plugin_and_both_versions() -> None:
    with pytest.raises(PluginContractError) as caught:
        assert_compatible(metadata(ApiVersion(9, 0)))
    assert caught.value.context["plugin"] == "exporter:stub"
    assert caught.value.context["supported_api_version"] == "1.0"
