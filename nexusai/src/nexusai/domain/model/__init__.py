"""Domain entities and value objects.

Framework-level models: the plugin descriptors, the reusable result and metadata
shapes, execution and configuration descriptions, and the ambient context handed
to components. Business entities -- records, jobs, site profiles, schemas -- are
introduced by the phases that own them, so that a type and the logic operating on
it arrive together.
"""

from __future__ import annotations

from nexusai.domain.model.analysis import (
    AnalysisResult,
    Characteristic,
    Confidence,
    Observation,
    RetrievalStrategy,
    StrategyRecommendation,
)
from nexusai.domain.model.assessment import (
    QualityMeasurement,
    QualityResult,
    Severity,
    ValidationIssue,
    ValidationResult,
)
from nexusai.domain.model.change import (
    ChangeSet,
    ChangeSummary,
    ChangeType,
    FieldDelta,
    RecordChange,
)
from nexusai.domain.model.checkpoint import Checkpoint, validate_checkpoint
from nexusai.domain.model.context import FrameworkContext
from nexusai.domain.model.descriptor import PluginDescriptor, PluginState
from nexusai.domain.model.execution import (
    ConfigurationSnapshot,
    ExecutionInfo,
    ExecutionStatus,
)
from nexusai.domain.model.extraction import (
    ExtractedValue,
    ExtractionMethod,
    ExtractionResult,
    FieldProvenance,
)
from nexusai.domain.model.job import Job, JobState, JobType
from nexusai.domain.model.metadata import EventMetadata, Metadata
from nexusai.domain.model.persistence import (
    ArtifactMetadata,
    ArtifactType,
    DatasetId,
    DatasetVersion,
    ExportManifest,
    OutcomeStatus,
    ReportManifest,
    SchemaVersion,
    StoredDataset,
)
from nexusai.domain.model.plugin import ApiVersion, ExtensionPoint, PluginMetadata
from nexusai.domain.model.processing import (
    ProcessedDataset,
    ProcessedField,
    ProcessedRecord,
    ProcessingContext,
)
from nexusai.domain.model.quality import QualityDimension, QualityGrade
from nexusai.domain.model.recovery import RecoveryAction, RecoveryDecision
from nexusai.domain.model.report import Report
from nexusai.domain.model.retrieval import (
    BrowserDirectives,
    Document,
    HttpVerb,
    RetrievalMethod,
    RetrievalRequest,
)
from nexusai.domain.model.rules import RuleOutcome
from nexusai.domain.model.schedule import (
    OverlapPolicy,
    Schedule,
    ScheduleExpression,
    ScheduleKind,
)
from nexusai.domain.model.status import JobStatus
from nexusai.domain.model.workflow import (
    FailurePolicy,
    StageDefinition,
    StageOutcome,
    StageStatus,
    WorkflowDefinition,
)

__all__ = [
    "AnalysisResult",
    "ApiVersion",
    "ArtifactMetadata",
    "ArtifactType",
    "BrowserDirectives",
    "ChangeSet",
    "ChangeSummary",
    "ChangeType",
    "Characteristic",
    "Checkpoint",
    "Confidence",
    "ConfigurationSnapshot",
    "DatasetId",
    "DatasetVersion",
    "Document",
    "EventMetadata",
    "ExecutionInfo",
    "ExecutionStatus",
    "ExportManifest",
    "ExtensionPoint",
    "ExtractedValue",
    "ExtractionMethod",
    "ExtractionResult",
    "FailurePolicy",
    "FieldDelta",
    "FieldProvenance",
    "FrameworkContext",
    "HttpVerb",
    "Job",
    "JobState",
    "JobStatus",
    "JobType",
    "Metadata",
    "Observation",
    "OutcomeStatus",
    "OverlapPolicy",
    "PluginDescriptor",
    "PluginMetadata",
    "PluginState",
    "ProcessedDataset",
    "ProcessedField",
    "ProcessedRecord",
    "ProcessingContext",
    "QualityDimension",
    "QualityGrade",
    "QualityMeasurement",
    "QualityResult",
    "RecordChange",
    "RecoveryAction",
    "RecoveryDecision",
    "Report",
    "ReportManifest",
    "RetrievalMethod",
    "RetrievalRequest",
    "RetrievalStrategy",
    "RuleOutcome",
    "Schedule",
    "ScheduleExpression",
    "ScheduleKind",
    "SchemaVersion",
    "Severity",
    "StageDefinition",
    "StageOutcome",
    "StageStatus",
    "StoredDataset",
    "StrategyRecommendation",
    "ValidationIssue",
    "ValidationResult",
    "WorkflowDefinition",
    "validate_checkpoint",
]
