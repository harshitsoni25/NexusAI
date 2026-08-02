"""The data-processing framework: engines and the pipeline that sequences them.

The engines are thin orchestrators over the domain ports: the transformation
engine applies transformer chains, the validation engine runs validators, the
rule engine runs rules, the quality engine scores dimensions, and the change
engine runs detectors. The :class:`ProcessingPipeline` sequences them into the
fixed order -- transform, validate, evaluate rules, assess quality, detect change
-- while keeping each stage replaceable.

Every engine reads registries of strategies, so a new transformer, validator,
rule, dimension or detector is added by registration, never by editing an engine.
"""

from __future__ import annotations

from nexusai.application.processing.change import ChangeDetectionEngine
from nexusai.application.processing.pipeline import (
    ProcessingPipeline,
    ProcessingRequest,
)
from nexusai.application.processing.quality import QualityEngine
from nexusai.application.processing.rules import RuleEngine
from nexusai.application.processing.transformation import (
    TransformationEngine,
    TransformationPlan,
)
from nexusai.application.processing.validation import ValidationEngine

__all__ = [
    "ChangeDetectionEngine",
    "ProcessingPipeline",
    "ProcessingRequest",
    "QualityEngine",
    "RuleEngine",
    "TransformationEngine",
    "TransformationPlan",
    "ValidationEngine",
]
