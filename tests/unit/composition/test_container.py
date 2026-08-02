"""The composition root."""

from __future__ import annotations

from pathlib import Path

import pytest

from nexusai.composition.container import Container, bootstrap, build_container
from nexusai.domain.errors import ConfigurationError
from nexusai.infrastructure.config.loader import ConfigurationLoader, LoadedConfiguration
from nexusai.testing import FrozenClock, RecordingLogger, SequentialIdGenerator


def test_the_container_exposes_every_wired_collaborator(container: Container) -> None:
    assert container.settings is not None
    assert container.logger is not None
    assert container.metrics is not None
    assert container.clock is not None
    assert container.events is not None
    assert container.plugins is not None


def test_the_container_is_immutable(container: Container) -> None:
    with pytest.raises(AttributeError):
        container.logger = RecordingLogger()  # type: ignore[misc]


def test_a_correlation_id_is_minted_for_the_run(container: Container) -> None:
    assert str(container.correlation_id) == "id-0001"


def test_startup_publishes_the_framework_started_event(
    configuration: LoadedConfiguration, ids: SequentialIdGenerator
) -> None:
    # Two identifiers are consumed: one for the run correlation, one for the
    # startup event. This is the cheapest observable proof the event was emitted.
    build_container(configuration, id_generator=ids)
    assert ids.counter == 2


def test_the_plugin_registry_is_frozen_before_execution(container: Container) -> None:
    # A registry that could change mid-run would mean two records in one dataset
    # might come from different implementations of the same extension point.
    assert container.plugins.frozen is True


def test_nested_correlation_ids_are_distinct(container: Container) -> None:
    assert container.new_correlation_id() != container.correlation_id


def test_substituted_doubles_are_used_rather_than_real_adapters(
    configuration: LoadedConfiguration,
) -> None:
    logger = RecordingLogger()
    clock = FrozenClock()
    container = build_container(configuration, clock=clock, logger=logger)
    assert container.logger is logger
    assert container.clock is clock


def test_bootstrap_loads_configuration_and_wires_in_one_step(tmp_path: Path) -> None:
    container = bootstrap(
        loader=ConfigurationLoader(packaged_defaults=None),
        overrides=(f"paths.root={tmp_path}",),
        environ={},
        logger=RecordingLogger(),
        clock=FrozenClock(),
        id_generator=SequentialIdGenerator(),
    )
    assert container.settings.paths.root == tmp_path


def test_bootstrap_fails_before_wiring_when_configuration_is_invalid() -> None:
    # A misconfigured invocation must cost no time and touch no external system.
    with pytest.raises(ConfigurationError):
        bootstrap(
            loader=ConfigurationLoader(packaged_defaults=None),
            overrides=("logging.level=NONSENSE",),
            environ={},
            logger=RecordingLogger(),
        )
