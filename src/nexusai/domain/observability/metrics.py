"""Vendor-neutral metric contracts and the operation-outcome taxonomy.

These are the pure vocabulary of observability: what kinds of metric exist, what
units they carry, what outcomes an operation can have, and how a metric is
described in the catalog. Nothing here records or emits anything -- that is
infrastructure -- and nothing here knows about Prometheus, OpenTelemetry or any
vendor. Keeping the vocabulary in the domain is what lets every layer speak about
metrics in the same terms while the concrete collector stays replaceable.

Cardinality is a first-class concern. A :class:`MetricDefinition` names the
dimensions a metric is allowed to carry, and those dimensions are meant to be
bounded categories -- an outcome, a format, an error category -- never an
unbounded value like a URL or an exception message. The catalog is the record of
that contract.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum


class MetricType(Enum):
    """The kind of a metric, which fixes how its samples are interpreted."""

    COUNTER = "counter"
    """A monotonically increasing total, such as requests attempted."""

    GAUGE = "gauge"
    """A point-in-time value that can rise and fall, such as active jobs."""

    HISTOGRAM = "histogram"
    """A distribution of observed values, summarised by percentiles."""

    TIMER = "timer"
    """A histogram whose observations are durations in seconds."""


class MetricUnit(Enum):
    """The unit a metric's values are expressed in.

    Units are explicit so that a duration is never accidentally recorded in
    milliseconds under a seconds-named metric. Counts are dimensionless.
    """

    SECONDS = "seconds"
    BYTES = "bytes"
    COUNT = "count"
    RATIO = "ratio"
    RECORDS = "records"
    PAGES = "pages"


class Outcome(Enum):
    """The stable outcome taxonomy shared across metrics and summaries.

    One vocabulary for "how did an operation end", reused everywhere rather than
    reinvented per subsystem, so a failure counted in retrieval means the same as
    a failure counted in export.
    """

    SUCCESS = "success"
    WARNING = "warning"
    PARTIAL = "partial"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    RETRIED = "retried"


_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


def is_valid_metric_name(name: str) -> bool:
    """Whether ``name`` follows the dotted, lower-snake naming standard.

    Names are dotted paths of lower-snake segments, such as
    ``nexusai.job.completed``. A valid name has at least two segments, so a
    metric always carries a namespace.
    """
    return bool(_NAME_PATTERN.match(name))


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricDefinition:
    """A catalog entry describing one metric.

    Attributes:
        name: The dotted metric name.
        metric_type: Counter, gauge, histogram or timer.
        unit: The unit the values carry.
        description: What the metric measures and how to read it.
        dimensions: The names of the bounded dimensions the metric may carry.
        interpretation: Guidance on what a change in the metric means.
    """

    name: str
    metric_type: MetricType
    unit: MetricUnit
    description: str
    dimensions: Sequence[str] = field(default_factory=tuple)
    interpretation: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "dimensions", tuple(self.dimensions))

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation for the published catalog."""
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "unit": self.unit.value,
            "description": self.description,
            "dimensions": list(self.dimensions),
            "interpretation": self.interpretation,
        }
