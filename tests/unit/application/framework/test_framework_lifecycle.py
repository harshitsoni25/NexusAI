"""Tests for the LifecycleManager and managed_lifecycle."""

from __future__ import annotations

import pytest

from nexusai.application.framework.lifecycle import (
    LifecycleManager,
    managed_lifecycle,
)
from nexusai.domain.events.base import ComponentDisposed, ComponentInitialized
from nexusai.domain.model.context import FrameworkContext
from nexusai.infrastructure.events.bus import InProcessEventBus
from nexusai.testing.fakes import RecordingLogger, RecordingSubscriber


class Component:
    """A lifecycle-aware component recording ordered lifecycle events."""

    def __init__(self, name: str, log: list[str], *, fail_init: bool = False) -> None:
        self.name = name
        self._log = log
        self._fail_init = fail_init

    def initialize(self) -> None:
        if self._fail_init:
            raise RuntimeError(f"{self.name} refused to start")
        self._log.append(f"init:{self.name}")

    def dispose(self) -> None:
        self._log.append(f"dispose:{self.name}")


def test_initialise_then_dispose_reverse_order(framework_context: FrameworkContext) -> None:
    log: list[str] = []
    manager = LifecycleManager(context=framework_context)
    manager.initialize([Component("a", log), Component("b", log)])
    manager.dispose()
    assert log == ["init:a", "init:b", "dispose:b", "dispose:a"]


def test_init_failure_disposes_already_started_and_reraises(
    framework_context: FrameworkContext,
) -> None:
    log: list[str] = []
    manager = LifecycleManager(context=framework_context)
    with pytest.raises(RuntimeError, match="refused to start"):
        manager.initialize([Component("a", log), Component("b", log, fail_init=True)])
    # 'a' was started, so it must be disposed before the error propagates.
    assert log == ["init:a", "dispose:a"]


def test_dispose_failure_is_logged_and_swallowed(framework_context: FrameworkContext) -> None:
    log: list[str] = []

    class FaultyDispose(Component):
        def dispose(self) -> None:
            raise RuntimeError("cannot dispose")

    manager = LifecycleManager(context=framework_context)
    manager.initialize([Component("a", log), FaultyDispose("b", log)])
    manager.dispose()  # must not raise
    assert "init:a" in log
    assert isinstance(framework_context.logger, RecordingLogger)
    assert framework_context.logger.has_message("failed to dispose")


def test_dispose_is_idempotent(framework_context: FrameworkContext) -> None:
    log: list[str] = []
    manager = LifecycleManager(context=framework_context)
    manager.initialize([Component("a", log)])
    manager.dispose()
    manager.dispose()
    assert log.count("dispose:a") == 1


def test_events_emitted_when_publisher_supplied(framework_context: FrameworkContext) -> None:
    log: list[str] = []
    bus = InProcessEventBus(logger=framework_context.logger, clock=framework_context.clock)
    subscriber = RecordingSubscriber(event_types=(ComponentInitialized, ComponentDisposed))
    bus.subscribe(subscriber)
    manager = LifecycleManager(context=framework_context, events=bus)
    manager.initialize([Component("a", log)])
    manager.dispose()
    kinds = [type(event) for event in subscriber.received]
    assert ComponentInitialized in kinds
    assert ComponentDisposed in kinds


def test_managed_lifecycle_disposes_on_exit(framework_context: FrameworkContext) -> None:
    log: list[str] = []
    with managed_lifecycle([Component("a", log)], framework_context):
        assert log == ["init:a"]
    assert log == ["init:a", "dispose:a"]


def test_managed_lifecycle_disposes_on_error(framework_context: FrameworkContext) -> None:
    log: list[str] = []
    with (
        pytest.raises(ValueError, match="body failed"),
        managed_lifecycle([Component("a", log)], framework_context),
    ):
        raise ValueError("body failed")
    assert log == ["init:a", "dispose:a"]


def test_manager_uses_type_name_when_component_has_no_name(
    framework_context: FrameworkContext,
) -> None:
    disposed: list[str] = []

    class Anonymous:
        # No 'name' attribute; the manager must fall back to the type name.
        def initialize(self) -> None:
            pass

        def dispose(self) -> None:
            disposed.append("x")

    manager = LifecycleManager(context=framework_context)
    manager.initialize([Anonymous()])
    manager.dispose()
    assert disposed == ["x"]
