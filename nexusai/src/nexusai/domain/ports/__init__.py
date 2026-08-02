"""Ports: the interfaces that the outer layers must satisfy.

Ports are declared as ``typing.Protocol`` rather than abstract base classes so
that an implementation need not import the domain in order to satisfy a contract.
Structural typing keeps plugin authors and infrastructure adapters decoupled from
framework internals while MyPy verifies conformance statically (ADR-0003).

Ports are named for the capability they provide, never for the technology that
happens to implement them: ``Exporter``, not ``CsvWriter``; ``StorageProvider``,
not ``SqlitePort``.

The observability, event and plugin ports are the framework primitives from
Phase 2. The persistence, strategy, validation, export, storage, reporting,
service and factory ports are the SDK contracts from Phase 3 that later feature
phases implement.
"""

from __future__ import annotations

from nexusai.domain.ports.application import (
    CheckpointStore,
    JobStore,
    ScheduleStore,
    SiteAdapter,
)
from nexusai.domain.ports.documents import (
    Extractor,
    Node,
    ParsedDocument,
    Parser,
)
from nexusai.domain.ports.events import EventPublisher, EventSubscriber
from nexusai.domain.ports.export import Exporter, StorageProvider
from nexusai.domain.ports.lifecycle_ports import Describable, Factory, Service
from nexusai.domain.ports.observability import Clock, IdGenerator, Logger, MetricsSink
from nexusai.domain.ports.persistence import (
    ReadableRepository,
    Repository,
    UnitOfWork,
    WritableRepository,
)
from nexusai.domain.ports.plugins import Plugin, PluginRegistry
from nexusai.domain.ports.processing import (
    ChangeDetector,
    QualityDimensionAssessor,
    Rule,
    Transformer,
)
from nexusai.domain.ports.reporting import ReportGenerator
from nexusai.domain.ports.retrieval import (
    PaginationStrategy,
    RecoveryPolicy,
    RetrievalProvider,
)
from nexusai.domain.ports.storage import (
    ArtifactStore,
    DatasetExporter,
    DatasetVersionStore,
    ReportRenderer,
)
from nexusai.domain.ports.strategy import ConditionalStrategy, Strategy
from nexusai.domain.ports.validation import Validator

__all__ = [
    "ArtifactStore",
    "ChangeDetector",
    "CheckpointStore",
    "Clock",
    "ConditionalStrategy",
    "DatasetExporter",
    "DatasetVersionStore",
    "Describable",
    "EventPublisher",
    "EventSubscriber",
    "Exporter",
    "Extractor",
    "Factory",
    "IdGenerator",
    "JobStore",
    "Logger",
    "MetricsSink",
    "Node",
    "PaginationStrategy",
    "ParsedDocument",
    "Parser",
    "Plugin",
    "PluginRegistry",
    "QualityDimensionAssessor",
    "ReadableRepository",
    "RecoveryPolicy",
    "ReportGenerator",
    "ReportRenderer",
    "Repository",
    "RetrievalProvider",
    "Rule",
    "ScheduleStore",
    "Service",
    "SiteAdapter",
    "StorageProvider",
    "Strategy",
    "Transformer",
    "UnitOfWork",
    "Validator",
    "WritableRepository",
]
