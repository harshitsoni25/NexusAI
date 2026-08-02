"""Infrastructure quality strategies for the data-processing framework."""

from __future__ import annotations

from nexusai.infrastructure.quality.dimensions import (
    AccuracyDimension,
    CompletenessDimension,
    ConsistencyDimension,
    IntegrityDimension,
    TimelinessDimension,
    UniquenessDimension,
)

__all__ = [
    "AccuracyDimension",
    "CompletenessDimension",
    "ConsistencyDimension",
    "IntegrityDimension",
    "TimelinessDimension",
    "UniquenessDimension",
]
