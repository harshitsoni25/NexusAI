"""Tests for the registry-backed ComponentFactory."""

from __future__ import annotations

import pytest

from nexusai.application.framework.factory import ComponentFactory, FactoryError
from nexusai.domain.model.context import FrameworkContext


class Widget:
    def __init__(self, context: FrameworkContext, tag: str) -> None:
        self.context = context
        self.tag = tag


def test_create_builds_with_injected_context(framework_context: FrameworkContext) -> None:
    factory: ComponentFactory[Widget] = ComponentFactory(framework_context)
    factory.register("plain", lambda ctx: Widget(ctx, "plain"))
    widget = factory.create("plain")
    assert widget.tag == "plain"
    assert widget.context is framework_context


def test_available_lists_registered_names(framework_context: FrameworkContext) -> None:
    factory: ComponentFactory[Widget] = ComponentFactory(framework_context)
    factory.register("b", lambda ctx: Widget(ctx, "b"))
    factory.register("a", lambda ctx: Widget(ctx, "a"))
    assert factory.available() == ("a", "b")


def test_create_unknown_name_raises_factory_error(framework_context: FrameworkContext) -> None:
    factory: ComponentFactory[Widget] = ComponentFactory(framework_context)
    with pytest.raises(FactoryError, match="No component builder named 'x'"):
        factory.create("x")


def test_create_propagates_builder_failure_as_factory_error(
    framework_context: FrameworkContext,
) -> None:
    factory: ComponentFactory[Widget] = ComponentFactory(framework_context)

    def broken(_: FrameworkContext) -> Widget:
        raise ValueError("nope")

    factory.register("broken", broken)
    with pytest.raises(FactoryError, match="builder for 'broken' failed: ValueError: nope"):
        factory.create("broken")


def test_freeze_blocks_further_registration(framework_context: FrameworkContext) -> None:
    from nexusai.shared.registry import RegistryError

    factory: ComponentFactory[Widget] = ComponentFactory(framework_context)
    factory.register("a", lambda ctx: Widget(ctx, "a"))
    factory.freeze()
    with pytest.raises(RegistryError, match="frozen"):
        factory.register("b", lambda ctx: Widget(ctx, "b"))
