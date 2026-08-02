"""Tests for the shared lifecycle protocols and mixin."""

from __future__ import annotations

from nexusai.shared.lifecycle import (
    Disposable,
    Initializable,
    LifecycleAware,
    LifecycleMixin,
    LifecycleState,
)


class TrackingComponent(LifecycleMixin):
    """A component recording how many times each phase ran."""

    def __init__(self) -> None:
        super().__init__()
        self.initialised = 0
        self.disposed = 0

    def initialize(self) -> None:
        self.initialised += 1
        super().initialize()

    def dispose(self) -> None:
        self.disposed += 1
        super().dispose()


def test_mixin_starts_in_created_state() -> None:
    assert TrackingComponent().lifecycle_state is LifecycleState.CREATED


def test_mixin_advances_through_states() -> None:
    component = TrackingComponent()
    component.initialize()
    after_init = component.lifecycle_state
    assert after_init is LifecycleState.INITIALISED
    component.dispose()
    after_dispose = component.lifecycle_state
    assert after_dispose is LifecycleState.DISPOSED


def test_default_mixin_methods_are_no_ops() -> None:
    component = LifecycleMixin()
    component.initialize()
    after_init = component.lifecycle_state
    assert after_init is LifecycleState.INITIALISED
    component.dispose()
    after_dispose = component.lifecycle_state
    assert after_dispose is LifecycleState.DISPOSED


def test_lifecycle_state_property_survives_missing_attribute() -> None:
    # A subclass that forgets to call super().__init__ still reads a sane default.
    class Forgetful(LifecycleMixin):
        def __init__(self) -> None:
            pass

    assert Forgetful().lifecycle_state is LifecycleState.CREATED


def test_protocols_are_satisfied_structurally() -> None:
    component = TrackingComponent()
    assert isinstance(component, Initializable)
    assert isinstance(component, Disposable)
    assert isinstance(component, LifecycleAware)


def test_lifecycle_states_are_distinct() -> None:
    assert len({LifecycleState.CREATED, LifecycleState.INITIALISED, LifecycleState.DISPOSED}) == 3
