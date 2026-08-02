"""Tests for FrameworkContext."""

from __future__ import annotations

from nexusai.domain.model.context import FrameworkContext
from nexusai.shared.identifiers import CorrelationId
from nexusai.testing.fakes import RecordingLogger


def test_for_component_binds_logger(framework_context: FrameworkContext) -> None:
    scoped = framework_context.for_component("exporter")
    scoped.logger.info("hello")
    assert isinstance(scoped.logger, RecordingLogger)
    assert scoped.logger.records[-1].fields["component"] == "exporter"


def test_for_component_shares_other_collaborators(framework_context: FrameworkContext) -> None:
    scoped = framework_context.for_component("x")
    assert scoped.clock is framework_context.clock
    assert scoped.correlation_id == framework_context.correlation_id


def test_nested_switches_correlation_and_binds_it(framework_context: FrameworkContext) -> None:
    nested = framework_context.nested(CorrelationId("nested-id"))
    assert nested.correlation_id == CorrelationId("nested-id")
    nested.logger.info("in nested")
    assert isinstance(nested.logger, RecordingLogger)
    assert nested.logger.records[-1].fields["correlation_id"] == "nested-id"


def test_new_correlation_id_uses_generator(framework_context: FrameworkContext) -> None:
    minted = framework_context.new_correlation_id()
    assert isinstance(minted, CorrelationId)
    assert str(minted)


def test_context_is_frozen(framework_context: FrameworkContext) -> None:
    import pytest

    with pytest.raises(AttributeError):
        framework_context.correlation_id = CorrelationId("other")  # type: ignore[misc]
