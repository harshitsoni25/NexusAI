"""The published extension point view."""

from __future__ import annotations

from nexusai.application.contracts import describe_extension_points
from nexusai.domain.model.plugin import ExtensionPoint


def test_every_extension_point_is_described() -> None:
    assert len(describe_extension_points()) == len(ExtensionPoint)


def test_descriptions_are_ordered_for_stable_display() -> None:
    names = [item.name for item in describe_extension_points()]
    assert names == sorted(names)


def test_each_description_carries_a_contract_version() -> None:
    for description in describe_extension_points():
        assert description.supported_api_version.major >= 1


def test_the_description_exposes_the_identifier_a_plugin_declares() -> None:
    first = describe_extension_points()[0]
    assert first.name == first.extension_point.value
