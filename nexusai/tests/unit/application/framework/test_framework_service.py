"""Tests for BaseService and CompositeService."""

from __future__ import annotations

from nexusai.application.framework.service import BaseService, CompositeService
from nexusai.domain.model.context import FrameworkContext
from nexusai.shared.lifecycle import LifecycleState
from nexusai.testing.fakes import RecordingLogger


class RecordingService(BaseService):
    """A service recording its lifecycle callbacks."""

    def __init__(self, name: str, context: FrameworkContext, log: list[str]) -> None:
        super().__init__(name, context)
        self._log = log

    def on_initialize(self) -> None:
        self._log.append(f"init:{self.name}")

    def on_dispose(self) -> None:
        self._log.append(f"dispose:{self.name}")


def test_service_binds_context_and_exposes_name(framework_context: FrameworkContext) -> None:
    service = RecordingService("svc", framework_context, [])
    assert service.name == "svc"
    service.context.logger.info("x")
    assert isinstance(service.context.logger, RecordingLogger)
    assert service.context.logger.records[-1].fields["component"] == "svc"


def test_initialize_and_dispose_run_hooks_once(framework_context: FrameworkContext) -> None:
    log: list[str] = []
    service = RecordingService("svc", framework_context, log)
    service.initialize()
    service.initialize()  # second call is a no-op
    service.dispose()
    service.dispose()  # second call is a no-op
    assert log == ["init:svc", "dispose:svc"]
    assert service.lifecycle_state is LifecycleState.DISPOSED


def test_dispose_before_initialise_is_safe(framework_context: FrameworkContext) -> None:
    log: list[str] = []
    service = RecordingService("svc", framework_context, log)
    service.dispose()
    assert log == ["dispose:svc"]
    assert service.lifecycle_state is LifecycleState.DISPOSED


def test_base_service_default_hooks_are_no_ops(framework_context: FrameworkContext) -> None:
    service = BaseService("plain", framework_context)
    service.initialize()
    service.dispose()
    assert service.lifecycle_state is LifecycleState.DISPOSED


def test_composite_initialises_in_order_disposes_in_reverse(
    framework_context: FrameworkContext,
) -> None:
    log: list[str] = []
    children = [RecordingService(name, framework_context, log) for name in ("a", "b", "c")]
    composite = CompositeService("parent", framework_context, children)
    composite.initialize()
    composite.dispose()
    assert log == [
        "init:a",
        "init:b",
        "init:c",
        "dispose:c",
        "dispose:b",
        "dispose:a",
    ]
    assert composite.children == tuple(children)


def test_composite_isolates_child_disposal_failure(
    framework_context: FrameworkContext,
) -> None:
    log: list[str] = []

    class Faulty(RecordingService):
        def on_dispose(self) -> None:
            raise RuntimeError("boom")

    children = [
        RecordingService("a", framework_context, log),
        Faulty("b", framework_context, log),
        RecordingService("c", framework_context, log),
    ]
    composite = CompositeService("parent", framework_context, children)
    composite.initialize()
    composite.dispose()  # must not raise despite child 'b' failing
    # a and c still disposed even though b raised.
    assert "dispose:a" in log
    assert "dispose:c" in log
    assert isinstance(framework_context.logger, RecordingLogger)
    assert framework_context.logger.has_message("failed to dispose")
