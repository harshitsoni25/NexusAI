"""Subsystem factories used by the composition root.

Kept separate from the container so that the root stays a readable list of what
gets wired to what, rather than a long function mixing wiring with construction
detail. Each factory answers one question: given the settings, which
implementation of this port should the run use?
"""

from __future__ import annotations

from nexusai.domain.ports.observability import Clock, IdGenerator, Logger, MetricsSink
from nexusai.infrastructure.config.settings import FrameworkSettings
from nexusai.infrastructure.observability.logging import configure_logging
from nexusai.infrastructure.observability.metrics import InMemoryMetricsSink
from nexusai.infrastructure.plugins.discovery import LoadReport, PluginDiscovery
from nexusai.infrastructure.plugins.registry import InMemoryPluginRegistry
from nexusai.infrastructure.runtime import SystemClock, Uuid4IdGenerator


def build_clock() -> Clock:
    """Return the clock implementation for this run."""
    return SystemClock()


def build_id_generator() -> IdGenerator:
    """Return the identifier generator for this run."""
    return Uuid4IdGenerator()


def build_logger(settings: FrameworkSettings) -> Logger:
    """Configure logging sinks and return the root logger."""
    return configure_logging(settings.logging, settings.paths)


def build_metrics(settings: FrameworkSettings) -> MetricsSink:  # noqa: ARG001
    """Return the metrics sink for this run.

    An in-memory sink is appropriate while every execution is a bounded CLI
    invocation: it costs nothing and gives the reporting layer something to
    summarise. Long-running scheduled jobs will need a bounded or streaming sink,
    which is a decision for the phase that introduces them. ``settings`` is
    accepted now so that the choice can become configuration-driven then without
    every caller changing.
    """
    return InMemoryMetricsSink()


def build_plugin_registry(
    settings: FrameworkSettings, logger: Logger
) -> tuple[InMemoryPluginRegistry, LoadReport]:
    """Discover plugins, register them, and close the registry.

    The registry is frozen before it is returned. Nothing may be registered once
    execution begins: a registry that changed mid-run would mean two records in
    one dataset could come from different implementations of the same extension
    point, leaving the run impossible to reason about afterwards.
    """
    registry = InMemoryPluginRegistry()
    report = PluginDiscovery(settings=settings.plugins, logger=logger).discover(registry)
    registry.freeze()
    return registry, report
