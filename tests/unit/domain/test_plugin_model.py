"""Plugin descriptors and the contract version rule."""

from __future__ import annotations

import pytest

from nexusai.domain.model.plugin import ApiVersion, ExtensionPoint, PluginMetadata


@pytest.mark.parametrize(
    ("raw", "expected"), [("1.0", (1, 0)), ("2.11", (2, 11)), (" 3.4 ", (3, 4))]
)
def test_versions_parse(raw: str, expected: tuple[int, int]) -> None:
    version = ApiVersion.parse(raw)
    assert (version.major, version.minor) == expected


@pytest.mark.parametrize("raw", ["1", "1.2.3", "x.y", "", "1."])
def test_malformed_versions_are_rejected(raw: str) -> None:
    with pytest.raises(ValueError, match="Invalid API version"):
        ApiVersion.parse(raw)


def test_negative_components_are_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        ApiVersion(-1, 0)


@pytest.mark.parametrize(
    ("plugin", "framework", "compatible"),
    [
        ((1, 0), (1, 0), True),
        ((1, 0), (1, 5), True),  # framework has grown additively since the plugin
        ((1, 6), (1, 5), False),  # plugin needs members the framework lacks
        ((2, 0), (1, 5), False),  # different major: breaking change
        ((1, 0), (2, 0), False),
    ],
)
def test_compatibility_follows_the_additive_only_rule(
    plugin: tuple[int, int], framework: tuple[int, int], compatible: bool
) -> None:
    assert ApiVersion(*plugin).is_compatible_with(ApiVersion(*framework)) is compatible


def test_versions_order_naturally() -> None:
    assert ApiVersion(1, 2) < ApiVersion(1, 10) < ApiVersion(2, 0)


def test_qualified_name_is_unique_across_extension_points() -> None:
    metadata = PluginMetadata("csv", "1.0.0", ExtensionPoint.EXPORTER, ApiVersion(1, 0))
    assert metadata.qualified_name == "exporter:csv"


@pytest.mark.parametrize(
    ("name", "version", "match"),
    [("", "1.0", "name must not be empty"), ("x", " ", "must declare a version")],
)
def test_metadata_requires_a_name_and_a_version(name: str, version: str, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        PluginMetadata(name, version, ExtensionPoint.EXPORTER, ApiVersion(1, 0))
