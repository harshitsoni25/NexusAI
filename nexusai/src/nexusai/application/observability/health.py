"""Operational health assessment from recorded metrics.

Health turns raw metrics into a verdict an operator can act on. Given the counters
and gauges a run recorded, and a set of thresholds, it computes runtime signals --
job failure rate, retry rate, queue saturation, error concentration -- and grades
each PASS, WARNING or FAIL. The thresholds are configuration, not magic numbers
buried in code, so an operator can tune what "unhealthy" means for their workload.

The assessment is pure with respect to the metrics it reads: it makes no request
and mutates nothing. It reports what the numbers say and where they crossed a line.
"""

from __future__ import annotations

from dataclasses import dataclass

from nexusai.domain.observability.health import (
    HealthCheck,
    HealthReport,
    HealthStatus,
    RuntimeSignal,
)
from nexusai.domain.ports.observability import MetricSink


@dataclass(frozen=True, slots=True, kw_only=True)
class HealthThresholds:
    """Thresholds that turn metric ratios into health statuses.

    Each pair is (warning, fail); a value at or above the warning threshold warns,
    and at or above the fail threshold fails.
    """

    failure_rate_warning: float = 0.10
    failure_rate_fail: float = 0.25
    retry_rate_warning: float = 0.20
    retry_rate_fail: float = 0.50
    queue_saturation_warning: float = 0.80
    queue_saturation_fail: float = 0.95


def _grade(value: float, warning: float, fail: float) -> HealthStatus:
    if value >= fail:
        return HealthStatus.FAIL
    if value >= warning:
        return HealthStatus.WARNING
    return HealthStatus.PASS


def assess_health(
    registry: MetricSink, *, thresholds: HealthThresholds | None = None
) -> HealthReport:
    """Assess operational health from the metrics a registry holds."""
    thresholds = thresholds or HealthThresholds()
    signals: list[RuntimeSignal] = []

    finished = registry.counter_total("nexusai.job.finished")
    failed = _finished_in_state(registry, "failed")
    if finished > 0:
        rate = failed / finished
        signals.append(
            RuntimeSignal(
                name="job_failure_rate",
                status=_grade(rate, thresholds.failure_rate_warning, thresholds.failure_rate_fail),
                value=rate,
                threshold=thresholds.failure_rate_warning,
                detail=f"{failed:.0f} of {finished:.0f} jobs failed",
            )
        )

    attempts = registry.counter_total("nexusai.request.attempted")
    retries = registry.counter_total("nexusai.retry.attempted")
    if attempts > 0:
        rate = retries / attempts
        signals.append(
            RuntimeSignal(
                name="retry_rate",
                status=_grade(rate, thresholds.retry_rate_warning, thresholds.retry_rate_fail),
                value=rate,
                threshold=thresholds.retry_rate_warning,
                detail=f"{retries:.0f} retries across {attempts:.0f} requests",
            )
        )

    depth, capacity = _queue(registry)
    if capacity > 0:
        saturation = depth / capacity
        signals.append(
            RuntimeSignal(
                name="queue_saturation",
                status=_grade(
                    saturation,
                    thresholds.queue_saturation_warning,
                    thresholds.queue_saturation_fail,
                ),
                value=saturation,
                threshold=thresholds.queue_saturation_warning,
                detail=f"queue at {depth:.0f} of {capacity:.0f}",
            )
        )

    checks = [
        HealthCheck(
            name=signal.name,
            status=signal.status,
            detail=signal.detail,
            remediation=(
                "" if signal.status is HealthStatus.PASS else "review recent runs and logs"
            ),
        )
        for signal in signals
    ]
    if not checks:
        checks.append(
            HealthCheck(
                name="activity",
                status=HealthStatus.PASS,
                detail="no completed activity yet to assess",
            )
        )
    return HealthReport(checks=checks)


def _finished_in_state(registry: MetricSink, state: str) -> float:
    return registry.counter_by_dimension("nexusai.job.finished", "state").get(state, 0.0)


def _queue(registry: MetricSink) -> tuple[float, float]:
    depth = registry.gauge_value("nexusai.queue.depth") or 0.0
    capacity = registry.gauge_value("nexusai.queue.capacity") or 0.0
    return depth, capacity
