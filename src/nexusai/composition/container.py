"""The composition root: the one place that knows both abstractions and adapters.

Every other module in the framework depends on ports. This module is where those
ports acquire implementations, which is the mechanism that lets the dependency
rule hold everywhere else (ADR-0001).

Wiring is explicit code rather than runtime lookup. An incorrectly wired system
therefore fails at startup with a type error that MyPy catches before the process
runs at all, instead of failing mid-execution with an ``AttributeError``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from nexusai.__about__ import __version__
from nexusai.composition import factories
from nexusai.domain.events.base import FrameworkStarted
from nexusai.domain.ports.observability import Clock, IdGenerator, Logger, MetricsSink
from nexusai.infrastructure.config.loader import ConfigurationLoader, LoadedConfiguration
from nexusai.infrastructure.config.settings import FrameworkSettings
from nexusai.infrastructure.events.bus import InProcessEventBus
from nexusai.infrastructure.plugins.discovery import LoadReport
from nexusai.infrastructure.plugins.registry import InMemoryPluginRegistry
from nexusai.shared.identifiers import CorrelationId


@dataclass(frozen=True, slots=True)
class Container:
    """Everything a run needs, wired and ready.

    Held by the presentation layer for the duration of a command and passed to
    use cases explicitly. It is not a service locator: consumers receive the
    specific collaborators they need through their constructors, and nothing
    reaches into the container at point of use.
    """

    settings: FrameworkSettings
    configuration: LoadedConfiguration
    logger: Logger
    metrics: MetricsSink
    clock: Clock
    id_generator: IdGenerator
    events: InProcessEventBus
    plugins: InMemoryPluginRegistry
    plugin_report: LoadReport
    correlation_id: CorrelationId

    def new_correlation_id(self) -> CorrelationId:
        """Mint a correlation identifier for a nested unit of work."""
        return CorrelationId(self.id_generator.new())


def build_container(
    configuration: LoadedConfiguration,
    *,
    clock: Clock | None = None,
    id_generator: IdGenerator | None = None,
    logger: Logger | None = None,
    metrics: MetricsSink | None = None,
) -> Container:
    """Wire the framework from validated configuration.

    The keyword arguments exist so that a test can substitute a frozen clock,
    deterministic identifiers or a recording logger without reaching into the
    container afterwards. Production callers pass none of them.
    """
    settings = configuration.settings
    resolved_clock = clock or factories.build_clock()
    resolved_ids = id_generator or factories.build_id_generator()
    resolved_logger = logger or factories.build_logger(settings)
    resolved_metrics = metrics or factories.build_metrics(settings)

    events = InProcessEventBus(logger=resolved_logger, clock=resolved_clock)
    registry, report = factories.build_plugin_registry(settings, resolved_logger)
    correlation_id = CorrelationId(resolved_ids.new())

    container = Container(
        settings=settings,
        configuration=configuration,
        logger=resolved_logger,
        metrics=resolved_metrics,
        clock=resolved_clock,
        id_generator=resolved_ids,
        events=events,
        plugins=registry,
        plugin_report=report,
        correlation_id=correlation_id,
    )
    events.publish(
        FrameworkStarted(
            event_id=resolved_ids.new(),
            occurred_at=resolved_clock.now(),
            correlation_id=correlation_id,
            source="nexusai.composition",
            version=__version__,
        )
    )
    return container


def bootstrap(
    *,
    config_file: Path | None = None,
    overrides: Sequence[str] = (),
    environ: Mapping[str, str] | None = None,
    loader: ConfigurationLoader | None = None,
    clock: Clock | None = None,
    id_generator: IdGenerator | None = None,
    logger: Logger | None = None,
    metrics: MetricsSink | None = None,
) -> Container:
    """Load configuration and wire the framework in one step.

    The single entry point used by the presentation layer.

    Raises:
        ConfigurationError: If configuration is missing, malformed or invalid.
            Raised before anything is wired, so a misconfigured invocation costs
            no time and touches no external system.
    """
    resolved_loader = loader or ConfigurationLoader()
    configuration = resolved_loader.load(
        config_file=config_file, overrides=overrides, environ=environ
    )
    return build_container(
        configuration,
        clock=clock,
        id_generator=id_generator,
        logger=logger,
        metrics=metrics,
    )
