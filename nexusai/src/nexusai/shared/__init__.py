"""Pure, general-purpose framework primitives, importable by every layer.

``shared`` holds the framework's dependency-free building blocks: value
primitives (identifiers, the result type, JSON types, sentinels) and the
general-purpose mechanisms every layer reuses (lifecycle, a typed registry, a
middleware pipeline, serialisation and mapping helpers).

Membership is restricted. A module belongs here only if it is pure, free of
third-party dependencies, holds no global state, and is genuinely general --
useful across several packages and layers with no business meaning. The pipeline
and registry hold instance-scoped state, which is permitted; global mutable state
is not. The restriction exists to keep this from becoming the utility dumping
ground the Master Specification forbids (see ADR-0015).
"""

from __future__ import annotations

from nexusai.shared.identifiers import CorrelationId, Identifier, JobId, RunId
from nexusai.shared.lifecycle import (
    Disposable,
    Initializable,
    LifecycleAware,
    LifecycleMixin,
    LifecycleState,
)
from nexusai.shared.pipeline import Middleware, Next, Pipeline
from nexusai.shared.registry import Registry, RegistryError
from nexusai.shared.result import Err, Ok, Result, is_err, is_ok
from nexusai.shared.serialization import SelfSerialising, to_primitive
from nexusai.shared.types import (
    UNSET,
    JsonMapping,
    JsonScalar,
    JsonValue,
    MutableJsonMapping,
    Unset,
)

__all__ = [
    "UNSET",
    "CorrelationId",
    "Disposable",
    "Err",
    "Identifier",
    "Initializable",
    "JobId",
    "JsonMapping",
    "JsonScalar",
    "JsonValue",
    "LifecycleAware",
    "LifecycleMixin",
    "LifecycleState",
    "Middleware",
    "MutableJsonMapping",
    "Next",
    "Ok",
    "Pipeline",
    "Registry",
    "RegistryError",
    "Result",
    "RunId",
    "SelfSerialising",
    "Unset",
    "is_err",
    "is_ok",
    "to_primitive",
]
